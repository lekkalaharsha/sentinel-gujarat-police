"""Multi-watchlist demo — 5 independent "camera feeds", 5 watchlist categories,
built on ONE real traffic video (demo_output/stock_footage/traffic_source.mp4).

Different shape from demo_end_to_end.py's single-vehicle cross-camera
journey: here each of 5 feeds is INDEPENDENT (its own designated plate, its
own watchlist category, its own camera/department, its own frame of the
video). There is no cross-camera identity resolution/journey narrative to
build, so the Re-ID false-matching fragility that made a continuous-journey
real-video attempt unreliable doesn't apply here — each feed is a single
real frame, resolved by an exact plate read.

Real video, real YOLOv8 detection, real PaddleOCR — the constructed part is
which real vehicle in each frame gets our designated plate composited onto
it (disclosed pattern, same as demo_end_to_end.py: "our own footage of
choice", not live sandbox feeds). Empirically, the plate patch needs the
WIDER margins (25-75% width, 60-90% height of the vehicle bbox) that
demo_end_to_end.py originally used, not the narrower ones later added there
for a different (multi-frame jitter) problem — on this video's more modest
vehicle-box sizes, the narrower patch was too small for reliable OCR.

Missing-persons is deliberately NOT one of the categories below — it needs
facial recognition, which STRATEGY.md's OUT list explicitly excludes
(legal/DPDP risk, documented bias, not needed for the required test case).

Run (from backend/, in the .venv with requirements-ml.txt installed):
    .venv\\Scripts\\python.exe scripts/demo_multi_watchlist.py                 # verify mode
    SENTINEL_DEMO_PERSIST=1 .venv\\Scripts\\python.exe scripts/demo_multi_watchlist.py   # populate real DB
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PERSIST = os.environ.get("SENTINEL_DEMO_PERSIST") == "1"

if not PERSIST:
    _DB_FD, _DB_PATH = tempfile.mkstemp(suffix="_sentinel_multi_demo.db")
    os.close(_DB_FD)
    os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

import cv2
import numpy as np

from app.analytics.detector import YoloVehicleDetector
from app.analytics.anpr import PaddleOcrPlateReader
from app.analytics.pipeline import AnalyticsPipeline
from app.db.models import Alert, CameraRegistry, VehicleEvent, VehicleIdentity
from app.db.session import SessionLocal, init_db
from app.streaming.rtsp_client import Frame
from app.watchlist.service import watchlist_service

SOURCE_VIDEO = os.path.join(
    os.path.dirname(__file__), "..", "..", "demo_output", "stock_footage", "traffic_source.mp4"
)

# Five independent feeds, five watchlist categories — each its own
# camera/department/plate/reason/frame of the source video. No two share a
# plate, so there is no cross-feed identity resolution to worry about.
# `at_seconds` are spread across the 12s clip so each feed's largest
# detected vehicle is a genuinely different real vehicle, not the same one
# restated.
FEEDS = [
    dict(camera_id="cam01", department="Police", location="Ahmedabad - Ring Road",
         lat=23.0225, lon=72.5714, plate="GJ01AB1234", reason="stolen", at_seconds=0.0),
    dict(camera_id="cam02", department="RTO", location="Ahmedabad - RTO Checkpost",
         lat=23.0300, lon=72.5800, plate="GJ03CD5678", reason="blacklisted", at_seconds=3.5),
    dict(camera_id="cam03", department="Highway Patrol", location="SG Highway",
         lat=23.0400, lon=72.5100, plate="GJ05EF9012", reason="suspect_vehicle", at_seconds=5.0),
    dict(camera_id="cam04", department="Municipal Corporation", location="CG Road Junction",
         lat=23.0338, lon=72.5619, plate="GJ01GH3456", reason="robbery_case", at_seconds=7.5),
    dict(camera_id="cam05", department="Panchayat", location="Gandhinagar - Sector 21",
         lat=23.2237, lon=72.6486, plate="GJ18JK7890", reason="hit_and_run", at_seconds=10.0),
]


def _grab_frame(video_path: str, at_seconds: float) -> np.ndarray:
    if not os.path.exists(video_path):
        raise RuntimeError(f"missing {video_path} — see demo_output/stock_footage/ for how it was fetched")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(at_seconds * fps))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"could not read frame at {at_seconds}s from {video_path}")
    return frame


def _make_plate_image(w: int, h: int, plate_text: str) -> np.ndarray:
    """Rendered at 4x then downscaled with anti-aliasing — PaddleOCR
    misread a blocky-rendered '0' as 'O' on one real test frame (95%
    confidence, silently rejected by the plate-format regex since "GJ" must
    be followed by digits). Supersampling gives smoother glyph edges,
    closer to how a real plate's stroke anti-aliasing looks in a camera
    frame, which measurably fixed that misread."""
    ss = 4
    plate = np.full((h * ss, w * ss, 3), 255, dtype=np.uint8)
    cv2.rectangle(plate, (2 * ss, 2 * ss), (w * ss - 3 * ss, h * ss - 3 * ss), (0, 0, 0), 2 * ss)
    scale = (w / 260.0) * ss
    cv2.putText(plate, plate_text, (int(12 * scale), int(h * ss * 0.68)),
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), max(1, int(3 * scale)), cv2.LINE_AA)
    return cv2.resize(plate, (w, h), interpolation=cv2.INTER_AREA)


def _frame_with_plate(base_img: np.ndarray, detector: YoloVehicleDetector, plate_text: str) -> np.ndarray:
    """Composite the designated plate onto the largest real vehicle detected
    in this real frame. WIDER margins (25-75% width, 60-90% height of the
    vehicle bbox) than demo_end_to_end.py's later narrowed version — see
    module docstring for why those don't transfer here."""
    frame = base_img.copy()
    dets = detector.detect(frame)
    candidates = sorted(
        (d for d in dets if d.label in ("bus", "car", "truck")),
        key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]),
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("no vehicle detected in this frame — cannot build the scenario")
    vehicle = candidates[0]
    x1, y1, x2, y2 = (int(v) for v in vehicle.bbox)
    cw, ch = x2 - x1, y2 - y1
    px1, px2 = x1 + int(cw * 0.25), x1 + int(cw * 0.75)
    py1, py2 = y1 + int(ch * 0.60), y1 + int(ch * 0.90)
    frame[py1:py2, px1:px2] = _make_plate_image(px2 - px1, py2 - py1, plate_text)
    return frame


def _drive_camera(pipeline: AnalyticsPipeline, camera_id: str, frame_img: np.ndarray, t_ms: float) -> None:
    pipeline.process(Frame(camera_id=camera_id, image=frame_img, pts_ms=t_ms, discontinuity=False))
    pipeline.process(Frame(camera_id=camera_id, image=frame_img, pts_ms=t_ms + 3000, discontinuity=True))


def main() -> int:
    init_db()
    session = SessionLocal()

    for feed in FEEDS:
        existing = session.get(CameraRegistry, feed["camera_id"])
        if existing is None:
            existing = CameraRegistry(id=feed["camera_id"])
            session.add(existing)
        existing.department = feed["department"]
        existing.location_name = feed["location"]
        existing.latitude = feed["lat"]
        existing.longitude = feed["lon"]

    watchlist_service.load(session)
    for feed in FEEDS:
        if watchlist_service.check(feed["plate"]) is None:
            watchlist_service.add(session, feed["plate"], feed["reason"])
    session.commit()

    print("Loading real models (YOLOv8 + PaddleOCR)...")
    plate_reader = PaddleOcrPlateReader()
    base_time = dt.datetime.utcnow() - dt.timedelta(minutes=5)
    pipeline = AnalyticsPipeline(
        detector_factory=lambda: YoloVehicleDetector(weights="yolov8n.pt"),
        plate_reader=plate_reader,
        clock=lambda: base_time,
    )

    print(f"\nRunning {len(FEEDS)} independent feeds (real frames from {os.path.basename(SOURCE_VIDEO)}) "
          "against the watchlist:")
    for i, feed in enumerate(FEEDS):
        # Fresh detector per feed — not shared/reused — avoids ByteTrack's
        # persist=True state leaking between unrelated frames (found and
        # fixed while building demo_end_to_end.py's real-video experiment).
        detector = YoloVehicleDetector(weights="yolov8n.pt")
        base_frame = _grab_frame(SOURCE_VIDEO, feed["at_seconds"])
        frame_img = _frame_with_plate(base_frame, detector, feed["plate"])
        _drive_camera(pipeline, feed["camera_id"], frame_img, i * 30_000.0)
        print(f"  {feed['camera_id']} ({feed['department']}, {feed['location']}) "
              f"— plate {feed['plate']} — watchlist reason: {feed['reason']}")

    print("\n=== VERIFYING EVALUATION OUTPUTS ===")
    ok = True
    for feed in FEEDS:
        identity = session.query(VehicleIdentity).filter_by(plate=feed["plate"]).first()
        if identity is None:
            print(f"FAIL: {feed['plate']} — no identity ever resolved")
            ok = False
            continue
        alerts = session.query(Alert).filter_by(plate=feed["plate"]).all()
        if alerts and alerts[0].reason == feed["reason"]:
            print(f"PASS: {feed['plate']} ({feed['reason']}) — alert id={alerts[0].id} camera={alerts[0].camera_id}")
        else:
            print(f"FAIL: {feed['plate']} — expected a '{feed['reason']}' alert, got {alerts}")
            ok = False

    session.close()
    if PERSIST:
        from app.db.session import engine
        engine.dispose()
        print(f"\n=== PERSISTED to {os.environ.get('DATABASE_URL', 'sentinel.db')} ===")
        print("Now start the API + frontend and record the demo against this data:")
        print("    .venv\\Scripts\\python.exe -m app.main       # backend on :8000")
        print("    (cd ../frontend && npm run dev)              # UI on :5173")
    else:
        from app.db.session import engine
        engine.dispose()
        try:
            os.unlink(_DB_PATH)
        except OSError:
            pass

    if ok:
        print("\n=== ALL 5 WATCHLIST CATEGORIES VERIFIED — MULTI-FEED DEMO WORKS END-TO-END ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
