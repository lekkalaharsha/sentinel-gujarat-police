"""End-to-end demo + integration test — the ACTUAL evaluation scenario.

Mirrors HACKATHON_DETAILS.md §8's live test case as closely as possible
WITHOUT the sandbox: a designated vehicle travels across several cameras;
at some cameras its plate is readable, at others it is not; the system must
still produce the complete timestamped cross-camera movement history and
raise a watchlist alert. Everything runs through the REAL pipeline
(YOLOv8 + PaddleOCR + identity resolution), not stubs or mocks — the only
synthetic part is the input frames (a real vehicle image with a plate
composited on), because we don't have live sandbox footage here.

This is deliberately a repo script, not a throwaway scratch file: it's both
the reproducible "does the whole thing actually work" proof and the driver
you run to populate a DB for a demo recording.

Run (from backend/, in the .venv with requirements-ml.txt installed):
    python scripts/demo_end_to_end.py                 # verify mode (throwaway DB)
    SENTINEL_DEMO_PERSIST=1 python scripts/demo_end_to_end.py   # populate real DB for a recording

Verify mode uses its own throwaway SQLite DB so it never touches a real one.
PERSIST mode writes to the app's real DB (DATABASE_URL, default sentinel.db)
and does NOT delete it — so you can then start the API + frontend and record
a demo exploring the populated results (map, timeline, alert). In PERSIST
mode the sightings' `observed_at` is set to a realistic simulated timeline
(see ROUTE `t_min`) so the geo-temporal route reconstruction reads as a
credible journey rather than a 5-camera dash in the few seconds the script
actually took to run.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PERSIST = os.environ.get("SENTINEL_DEMO_PERSIST") == "1"

# Verify mode: isolated throwaway DB (must be set before any app.db import).
# PERSIST mode: leave DATABASE_URL as-is (app default = sentinel.db) so the
# running API server serves exactly what this script populated.
if not PERSIST:
    _DB_FD, _DB_PATH = tempfile.mkstemp(suffix="_sentinel_demo.db")
    os.close(_DB_FD)
    os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

import cv2
import numpy as np

# ORDER MATTERS (Windows torch/paddle DLL conflict — see main.py): detector
# before plate reader.
from app.analytics.detector import YoloVehicleDetector
from app.analytics.anpr import PaddleOcrPlateReader
from app.analytics.pipeline import AnalyticsPipeline
from app.db.models import Alert, CameraRegistry, VehicleEvent, VehicleIdentity, WatchlistEntry
from app.db.session import SessionLocal, init_db
from app.streaming.rtsp_client import Frame
from app.watchlist.service import watchlist_service

DESIGNATED_PLATE = "GJ01AB1234"

# The simulated route: a vehicle moving across 5 cameras in 5 departments.
# `plate_readable` mirrors real conditions — glare/angle/blur mean the plate
# is only cleanly readable at SOME cameras, not all. The whole point of the
# system is that the vehicle is still tracked across the ones where it isn't.
# `t_min` = minutes from journey start; used in PERSIST mode to stamp a
# realistic observed_at so the geo route reconstruction reads as a credible
# ~78-minute Ahmedabad->Kalol drive (each inter-camera hop is a plausible
# 30-45 km/h city/highway speed — verified against analytics/geo.py).
# columns: id, department, location, lat, lon, plate_readable, t_min
ROUTE = [
    ("cam01", "Police",                 "Ahmedabad - CG Road Jn",  23.0338, 72.5619, False, 0),
    ("cam02", "Municipal Corporation",  "Ahmedabad - SG Highway",  23.0300, 72.5100, False, 8),
    ("cam03", "GSRTC",                  "Gandhinagar - ST Depot",  23.2237, 72.6486, True,  43),  # <- plate read here
    ("cam04", "Health",                 "Gandhinagar - Civil Hosp",23.2200, 72.6500, False, 48),
    ("cam05", "Panchayat",              "Kalol - Gram Chowk",      23.2450, 72.4900, False, 78),
]


def _load_vehicle_image() -> np.ndarray:
    """A real vehicle image YOLO will actually detect. ultralytics ships
    bus.jpg in its ASSETS, so this stays self-contained — no network, no
    committed binary."""
    from ultralytics.utils import ASSETS

    img = cv2.imread(str(ASSETS / "bus.jpg"))
    if img is None:
        raise RuntimeError("could not load ultralytics ASSETS/bus.jpg")
    return img


def _make_plate_image(w: int, h: int) -> np.ndarray:
    plate = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.rectangle(plate, (2, 2), (w - 3, h - 3), (0, 0, 0), 2)
    scale = w / 260.0
    cv2.putText(plate, DESIGNATED_PLATE, (int(12 * scale), int(h * 0.68)),
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), max(1, int(3 * scale)))
    return plate


def _frame_for_camera(base_img: np.ndarray, detector: YoloVehicleDetector, readable: bool) -> np.ndarray:
    """Composite the designated plate onto the vehicle's plate region if the
    plate is 'readable' at this camera; otherwise leave the region blank (a
    genuinely unreadable plate — PaddleOCR really returns nothing, we don't
    fake the failure)."""
    frame = base_img.copy()
    dets = detector.detect(frame)
    vehicle = next((d for d in dets if d.label in ("bus", "car", "truck")), None)
    if vehicle is None:
        raise RuntimeError("no vehicle detected in the base image — cannot build the scenario")
    x1, y1, x2, y2 = (int(v) for v in vehicle.bbox)
    cw, ch = x2 - x1, y2 - y1
    px1, px2 = x1 + int(cw * 0.25), x1 + int(cw * 0.75)
    py1, py2 = y1 + int(ch * 0.60), y1 + int(ch * 0.90)
    if readable:
        frame[py1:py2, px1:px2] = _make_plate_image(px2 - px1, py2 - py1)
    else:
        # Blank, plate-less region — the honest "can't read it here" case.
        frame[py1:py2, px1:px2] = np.full((py2 - py1, px2 - px1, 3), 210, dtype=np.uint8)
    return frame


def _drive_camera(pipeline: AnalyticsPipeline, camera_id: str, frame_img: np.ndarray, t_ms: float) -> None:
    """Feed a camera's frames through the real pipeline, then a discontinuity
    to force the in-flight track to finalize now (same mechanism as the
    sandbox's recording-loop cut) instead of waiting out the timeout."""
    pipeline.process(Frame(camera_id=camera_id, image=frame_img, pts_ms=t_ms, discontinuity=False))
    pipeline.process(Frame(camera_id=camera_id, image=frame_img, pts_ms=t_ms + 3000, discontinuity=True))


def main() -> int:
    init_db()
    session = SessionLocal()

    # 1. Onboard the route's cameras with department + GIS (Model 1).
    for cam_id, dept, loc, lat, lon, _, _ in ROUTE:
        session.add(CameraRegistry(id=cam_id, department=dept, location_name=loc, latitude=lat, longitude=lon))
    # 2. Put the designated vehicle on the watchlist (stolen).
    watchlist_service.load(session)
    watchlist_service.add(session, DESIGNATED_PLATE, "stolen")
    session.commit()

    print("Loading real models (YOLOv8 + PaddleOCR)...")
    detector = YoloVehicleDetector(weights="yolov8n.pt")
    plate_reader = PaddleOcrPlateReader()
    # One detector per camera (ByteTrack's persistent state must not be shared
    # across cameras — see pipeline.py). Both model families are already
    # imported here, so building more YOLO instances after PaddleOCR is safe
    # (the Windows DLL constraint is about import order, not construction).
    pipeline = AnalyticsPipeline(
        detector_factory=lambda: YoloVehicleDetector(weights="yolov8n.pt"),
        plate_reader=plate_reader,
    )

    base_img = _load_vehicle_image()

    print(f"\nSimulating '{DESIGNATED_PLATE}' traveling across {len(ROUTE)} cameras:")
    t0 = 0.0
    for i, (cam_id, dept, loc, _, _, readable, _t_min) in enumerate(ROUTE):
        frame_img = _frame_for_camera(base_img, detector, readable)
        _drive_camera(pipeline, cam_id, frame_img, t0 + i * 30_000)  # 30s of PTS between cameras
        print(f"  {cam_id} ({dept}, {loc}) — plate {'READABLE' if readable else 'unreadable'}")

    # PERSIST mode: stamp a realistic observed_at timeline so geo route
    # reconstruction reads as a credible journey (the script itself runs in
    # seconds; without this every hop would look like an impossible dash).
    if PERSIST:
        t_min_by_cam = {cam_id: t_min for cam_id, *_rest, t_min in ROUTE}
        base_time = dt.datetime(2026, 9, 7, 9, 0, 0)
        for e in session.query(VehicleEvent).all():
            e.observed_at = base_time + dt.timedelta(minutes=t_min_by_cam.get(e.camera_id, 0))
        session.commit()

    # ---- Verify the evaluation outputs, the way a judge would ----
    print("\n=== VERIFYING EVALUATION OUTPUTS ===")
    ok = True

    identity = session.query(VehicleIdentity).filter_by(plate=DESIGNATED_PLATE).first()
    if identity is None:
        print(f"FAIL: no identity ever resolved to {DESIGNATED_PLATE}")
        return 1

    events = (
        session.query(VehicleEvent)
        .filter_by(identity_id=identity.id)
        .order_by(VehicleEvent.pts_ms.asc())
        .all()
    )

    # (a) Complete cross-camera movement history — ALL cameras, including the
    #     ones where the plate was never read at that camera.
    seen_cameras = [e.camera_id for e in events]
    expected = [c[0] for c in ROUTE]
    print(f"\n(a) Movement history: {len(events)} sightings across cameras {seen_cameras}")
    if sorted(set(seen_cameras)) == sorted(expected):
        print(f"    PASS — all {len(expected)} cameras on the route are in the history")
    else:
        print(f"    FAIL — expected {expected}, got {sorted(set(seen_cameras))}")
        ok = False

    # (b) The anonymous sightings (plate unreadable at that camera) are still
    #     attributed to this plate's identity — the core claim.
    anon = [e for e in events if e.plate is None]
    readable_events = [e for e in events if e.plate is not None]
    print(f"\n(b) {len(anon)} sighting(s) had NO readable plate at their camera but are still")
    print(f"    in {DESIGNATED_PLATE}'s history via appearance linkage; {len(readable_events)} had a direct read.")
    if len(anon) >= 1 and len(readable_events) >= 1:
        print("    PASS — ANPR failure did not mean tracking failure")
    else:
        print("    FAIL — expected a mix of readable and unreadable-plate sightings")
        ok = False

    # (c) Timestamps present and ordered.
    print("\n(c) Timestamped, location-wise route:")
    for e in events:
        cam = session.get(CameraRegistry, e.camera_id)
        tag = "plate read here" if e.plate else "matched by appearance"
        print(f"    t+{e.pts_ms/1000:5.0f}s  {e.camera_id}  {cam.department:22} {cam.location_name:26} [{tag}]")

    # (d) Watchlist alert raised.
    alerts = session.query(Alert).filter_by(plate=DESIGNATED_PLATE).all()
    print(f"\n(d) Watchlist alerts raised for {DESIGNATED_PLATE}: {len(alerts)}")
    if alerts:
        for a in alerts:
            print(f"    ALERT id={a.id} camera={a.camera_id} reason={a.reason}")
        print("    PASS — cross-referencing a live sighting against the watchlist fired an alert")
    else:
        print("    FAIL — no alert raised despite a watchlisted plate being seen")
        ok = False

    # (e) Explainability data present on the appearance-linked sightings.
    upgraded = [e for e in events if e.link_method in ("plate_upgrade", "appearance_match")]
    print(f"\n(e) Explainability: {len(upgraded)} sighting(s) carry link method + Re-ID similarity score")
    if upgraded and all(e.link_score is not None for e in upgraded):
        print("    PASS — 'why was this linked?' data is populated")
    else:
        print("    FAIL — appearance-linked sightings are missing their link score")
        ok = False

    session.close()
    if PERSIST:
        from app.db.session import engine
        engine.dispose()  # release the handle so the API server can open the DB
        print(f"\n=== PERSISTED to {os.environ.get('DATABASE_URL', 'sentinel.db')} ===")
        print("Now start the API + frontend and record the demo against this data:")
        print("    python -m app.main            # backend on :8000")
        print("    (cd ../frontend && npm run dev)  # UI on :5173")
        print(f"Designated plate to search: {DESIGNATED_PLATE}  (watchlisted 'stolen')")
    else:
        # Dispose the engine so SQLite releases the file handle before unlink
        # (Windows won't delete a file another handle still holds).
        from app.db.session import engine
        engine.dispose()
        try:
            os.unlink(_DB_PATH)
        except OSError:
            pass  # throwaway temp file; not worth failing the run over

    print("\n" + ("=== ALL EVALUATION OUTPUTS VERIFIED — DEMO WORKS END-TO-END ==="
                  if ok else "=== SOME CHECKS FAILED — see above ==="))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
