"""Model 4 pilot slice: real detector aggregation and read-only rollups."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pytest
from sqlalchemy.orm import sessionmaker

from app.analytics.anpr import StubPlateReader
from app.analytics.density import storage_tier_for
from app.analytics.detector import Detection
from app.analytics.pipeline import AnalyticsPipeline
from app.analytics.face_recognition import DeliberatelyExcludedFaceRecognizer
from app.api.auth import Principal
from app.api.routes_admin import central_rollup, density_windows
from app.db.models import CameraDensityWindow, CameraRegistry, FederatedEvent
from app.streaming.rtsp_client import Frame


class _Detector:
    def detect(self, _image):
        return [
            Detection("car", 0.9, (1, 1, 20, 20)),
            Detection("person", 0.8, (30, 1, 50, 25)),
        ]


def test_pipeline_persists_real_detector_counts_per_window(session, monkeypatch):
    """Exercise pipeline -> detector output -> persisted density row, not just math."""
    import app.analytics.pipeline as pipeline_module

    Session = sessionmaker(bind=session.get_bind())
    monkeypatch.setattr(pipeline_module, "SessionLocal", Session)
    pipeline = AnalyticsPipeline(detector_factory=_Detector, plate_reader=StubPlateReader())
    pipeline.process(Frame("cam_density", np.zeros((80, 80, 3), dtype=np.uint8), 1000.0, False))

    row = session.query(CameraDensityWindow).one()
    assert row.camera_id == "cam_density"
    assert row.sampled_frames == 1
    assert row.vehicle_detections == 1
    assert row.person_detections == 1
    assert session.get(CameraRegistry, "cam_density") is not None


def test_storage_tier_is_age_based_not_a_storage_backend():
    now = dt.datetime(2026, 9, 13)
    assert storage_tier_for(now - dt.timedelta(days=1), now) == "hot"
    assert storage_tier_for(now - dt.timedelta(days=16), now) == "warm"
    assert storage_tier_for(now - dt.timedelta(days=366), now) == "cold"


def test_face_recognition_seam_never_returns_a_fabricated_result():
    with pytest.raises(RuntimeError, match="deliberately excluded"):
        DeliberatelyExcludedFaceRecognizer().identify(np.zeros((1, 1, 3)))


def test_admin_density_and_central_rollup_use_persisted_pilot_data(session):
    session.add_all([
        CameraRegistry(id="cam_police", department="Police", is_healthy=True),
        CameraRegistry(id="cam_health", department="Health", is_healthy=False),
        CameraDensityWindow(
            camera_id="cam_police", window_started_at=dt.datetime(2026, 9, 13), window_seconds=60,
            sampled_frames=4, vehicle_detections=7, person_detections=3,
        ),
        FederatedEvent(source_system="sentinel", plate="GJ01AB1234", observed_at=dt.datetime(2026, 9, 13), camera_id="cam_police"),
    ])
    session.commit()
    admin = Principal("admin", "admin", None)

    density = density_windows(db=session, _principal=admin)
    assert density["windows"][0]["vehicle_detections"] == 7
    assert density["count_semantics"].startswith("sampled-frame")

    rollup = central_rollup(db=session, _principal=admin)
    assert rollup["scope"].startswith("pilot rollup")
    assert rollup["cameras_by_department"] == {"Health": 1, "Police": 1}
    assert rollup["health"] == {"healthy": 1, "unhealthy": 1, "unknown": 0}
    assert rollup["federation"] == {"event_count": 1, "sources_present": ["sentinel"]}
