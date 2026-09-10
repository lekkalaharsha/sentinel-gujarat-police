from __future__ import annotations

import datetime as dt
import logging
import os
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .analytics.anpr import PaddleOcrPlateReader, StubPlateReader
from .analytics.detector import StubVehicleDetector, YoloVehicleDetector
from .analytics.pipeline import AnalyticsPipeline
from .analytics.plate_detector import StubPlateDetector, YoloPlateDetector
from .api import (
    routes_admin,
    routes_alerts,
    routes_auth,
    routes_cameras,
    routes_stream,
    routes_vehicle,
    routes_watchlist,
)
from .api.auth import ensure_default_admin_key
from .catalogue import catalogue
from .db.models import CameraRegistry
from .db.retention import purge_expired
from .db.session import SessionLocal, init_db
from .streaming.manager import StreamManager
from .watchlist.service import watchlist_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sentinel.main")

app = FastAPI(title="Sentinel — Unified CCTV Viewing & Analytics (Model 1 + 2)")
app.add_middleware(
    CORSMiddleware, allow_origins=config.CORS_ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)

app.include_router(routes_auth.router)
app.include_router(routes_cameras.router)
app.include_router(routes_vehicle.router)
app.include_router(routes_watchlist.router)
app.include_router(routes_alerts.router)
app.include_router(routes_stream.router)
app.include_router(routes_admin.router)

def _build_detector():
    """Real YOLOv8 vehicle detector if ultralytics + weights are available
    (see analytics/detector.py); falls back to the honest no-op stub
    otherwise, loudly, rather than silently pretending detection works."""
    try:
        return YoloVehicleDetector(weights=config.YOLO_WEIGHTS)
    except Exception as exc:  # noqa: BLE001 — ultralytics missing, weights unreachable, etc.
        logger.warning(
            "YOLOv8 detector unavailable (%s) — falling back to StubVehicleDetector "
            "(no detections will be produced). Run `pip install ultralytics` in a "
            "venv to enable real detection.",
            exc,
        )
        return StubVehicleDetector()


def _build_plate_detector():
    """Real trained plate localizer if the (separately downloaded) ONNX
    weights are present — see config.PLATE_DETECTOR_WEIGHTS. Falls back to
    StubPlateDetector's heuristic crop otherwise, loudly, same honest-
    fallback pattern as the detector/OCR builders above."""
    if not os.path.exists(config.PLATE_DETECTOR_WEIGHTS):
        logger.warning(
            "Plate localizer weights not found at %s — falling back to StubPlateDetector's "
            "heuristic crop (see config.PLATE_DETECTOR_WEIGHTS for the download command).",
            config.PLATE_DETECTOR_WEIGHTS,
        )
        return StubPlateDetector()
    try:
        return YoloPlateDetector(weights=config.PLATE_DETECTOR_WEIGHTS)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Plate localizer unavailable (%s) — falling back to StubPlateDetector's heuristic crop.",
            exc,
        )
        return StubPlateDetector()


def _build_plate_reader():
    """Real PaddleOCR plate reader if paddleocr/paddlepaddle are available
    (see analytics/anpr.py); falls back to the honest no-op stub otherwise."""
    try:
        return PaddleOcrPlateReader()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "PaddleOCR reader unavailable (%s) — falling back to StubPlateReader "
            "(no plates will ever be read). Run `pip install paddleocr==2.9.1 "
            "paddlepaddle==2.6.2` in a venv to enable real ANPR.",
            exc,
        )
        return StubPlateReader()


# ORDER MATTERS: build a detector (imports torch, via ultralytics) BEFORE
# the plate reader (imports paddlepaddle). Verified empirically on Windows —
# importing paddleocr/paddlepaddle first corrupts torch's DLL loading
# (`OSError: ... torch\lib\shm.dll ...`) when torch is imported afterward in
# the same process; the reverse order works fine. This isn't Python argument
# evaluation order being relied on implicitly — these are separate
# statements specifically so the required order stays visible and can't be
# silently broken by refactoring the AnalyticsPipeline(...) call below.
#
# This eager instance is discarded — AnalyticsPipeline builds its own
# detector PER CAMERA (see pipeline.py) because YoloVehicleDetector now
# carries persistent ByteTrack state (persist=True) that must not be shared
# across concurrent camera streams. The eager call here still matters: it's
# what forces torch to import before paddle, and it fails fast (falling
# back to a logged warning) at startup rather than on the first live frame.
_build_detector()
_plate_reader = _build_plate_reader()


pipeline = AnalyticsPipeline(
    detector_factory=_build_detector, plate_reader=_plate_reader, plate_detector=_build_plate_detector()
)
stream_manager = StreamManager(catalogue, on_frame=pipeline.process)


def _sync_camera_health() -> None:
    """Model 1's 'health monitoring' deliverable: reflect each onboarded
    camera's real connection state (from the RTSP worker, not a stub) into
    CameraRegistry so /cameras and /cameras/gap-analysis report it."""
    snapshot = stream_manager.health_snapshot()
    session = SessionLocal()
    try:
        now = time.time()
        for cam_id, status in snapshot.items():
            registry = session.get(CameraRegistry, cam_id)
            if registry is None:
                registry = CameraRegistry(id=cam_id)
                session.add(registry)
            stale = status["last_frame_at"] is None or (now - status["last_frame_at"]) > routes_cameras.HEALTH_STALE_S
            registry.is_healthy = status["connected"] and not stale
            if status["last_frame_at"] is not None:
                registry.last_seen_live_at = dt.datetime.utcfromtimestamp(status["last_frame_at"])
        # Cameras that were live before but have no active worker anymore
        # (dropped from the catalogue) are unhealthy, not silently unknown.
        active_ids = set(snapshot.keys())
        for registry in session.query(CameraRegistry).all():
            if registry.id not in active_ids and registry.is_healthy:
                registry.is_healthy = False
        session.commit()
    finally:
        session.close()


@app.on_event("startup")
def on_startup():
    init_db()
    session = SessionLocal()
    try:
        watchlist_service.load(session)
        ensure_default_admin_key(session)
    finally:
        session.close()

    catalogue.refresh()
    stream_manager.reconcile()
    catalogue.start_background_refresh()

    def reconcile_loop():
        while True:
            time.sleep(config.CATALOGUE_REFRESH_INTERVAL_S)
            stream_manager.reconcile()
            _sync_camera_health()

    threading.Thread(target=reconcile_loop, name="stream-reconcile", daemon=True).start()

    def retention_loop():
        # Enforce the DPDP storage-limitation retention policy on a slow
        # interval (see db/retention.py). Runs once at startup too, so a
        # long-idle deployment purges promptly on restart.
        while True:
            try:
                session = SessionLocal()
                try:
                    purge_expired(session)
                finally:
                    session.close()
            except Exception:  # noqa: BLE001 — a purge failure must not kill the loop
                logger.exception("retention purge failed")
            time.sleep(config.RETENTION_SWEEP_INTERVAL_S)

    threading.Thread(target=retention_loop, name="retention-sweep", daemon=True).start()
    logger.info("Sentinel backend started. CDN host=%s stream host=%s", config.CDN_HOST, config.STREAM_HOST)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_camera_workers": stream_manager.active_camera_ids,
        "catalogue_size": len(catalogue.cameras),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.API_HOST, port=config.API_PORT, reload=False)
