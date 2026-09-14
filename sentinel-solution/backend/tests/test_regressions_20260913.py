"""Focused regressions for accumulated-data and timing safety fixes."""
from __future__ import annotations

import datetime as dt

import numpy as np
from sqlalchemy import create_engine, text

from app.analytics.anpr_suitability import anpr_suitability_by_camera
from app.analytics.identity import IdentityResolver
from app.api.auth import Principal
from app.api.routes_cameras import catalogue, list_cameras
from app.db import session as db_session
from app.db.models import CameraRegistry, VehicleEvent, VehicleIdentity
from app.streaming import rtsp_client


def test_default_ffmpeg_options_force_tcp_and_bound_socket_reads():
    options = rtsp_client.os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
    assert "rtsp_transport;tcp" in options
    assert "stimeout;" in options


def test_duplicate_identity_migration_absorbs_data_and_logs_conflicts(tmp_path, monkeypatch, caplog):
    """A legacy DB can contain conflicting duplicate rows; neither the useful
    camera/embedding nor the fact of a disagreement may silently disappear."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE vehicle_identity (
                id INTEGER PRIMARY KEY, plate VARCHAR, plate_confidence FLOAT,
                embedding_json VARCHAR, first_seen_at DATETIME, last_seen_at DATETIME,
                last_camera_id VARCHAR
            )
        """))
        conn.execute(text("CREATE TABLE vehicle_event (id INTEGER PRIMARY KEY, identity_id INTEGER)"))
        conn.execute(text("""
            INSERT INTO vehicle_identity VALUES
            (1, 'GJ01AB1234', 0.50, NULL, '2026-01-01', '2026-01-01', NULL),
            (2, 'GJ01AB1234', 0.90, '[0.1,0.2]', '2026-02-01', '2026-02-01', 'cam-rich')
        """))
        conn.execute(text("INSERT INTO vehicle_event VALUES (11, 2)"))
    monkeypatch.setattr(db_session, "engine", engine)

    db_session._ensure_vehicle_identity_plate_unique({"vehicle_identity", "vehicle_event"})

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM vehicle_identity WHERE id = 1")).mappings().one()
        assert row["embedding_json"] == "[0.1,0.2]"
        assert row["last_camera_id"] == "cam-rich"
        assert row["plate_confidence"] == 0.50  # deterministic keeper wins conflicts
        # Real bug found reviewing this fix: first_seen_at/last_seen_at are
        # NOT arbitrary keeper-wins-conflicts fields like plate_confidence
        # above -- they have a genuinely correct merged value (MIN/MAX
        # across all duplicates). The keeper (id=1) is the earliest-CREATED
        # row, but the duplicate (id=2) proves the vehicle was actually
        # last seen a full month later, from a different camera -- that
        # must win, not be silently discarded as a "conflict".
        assert row["first_seen_at"] == "2026-01-01"
        assert row["last_seen_at"] == "2026-02-01"
        assert conn.execute(text("SELECT identity_id FROM vehicle_event WHERE id = 11")).scalar_one() == 1
    assert "plate_confidence" in caplog.text
    assert "0.5" in caplog.text and "0.9" in caplog.text
    engine.dispose()


def test_identity_and_event_can_be_rolled_back_together(session):
    """Resolver must not commit before its caller can persist the event."""
    session.add(CameraRegistry(id="cam_atomic"))
    session.commit()
    embedding = np.ones(48, dtype=np.float32)
    identity, _ = IdentityResolver().resolve(
        session, "GJ01ATOMIC", 0.9, embedding, dt.datetime(2026, 9, 13), "cam_atomic"
    )
    session.add(VehicleEvent(identity_id=identity.id, camera_id="cam_atomic", pts_ms=0.0))
    session.rollback()  # models an event insert/commit failure in pipeline finalization
    assert session.query(VehicleIdentity).filter_by(plate="GJ01ATOMIC").count() == 0
    assert session.query(VehicleEvent).count() == 0


def test_camera_anpr_suitability_uses_real_plate_history_only(session):
    session.add_all([CameraRegistry(id="cam_good"), CameraRegistry(id="cam_bad")])
    good_identity = VehicleIdentity(plate="GJ01GOOD")
    bad_identity = VehicleIdentity()
    session.add_all([good_identity, bad_identity])
    session.flush()
    for n in range(5):
        session.add(VehicleEvent(identity_id=good_identity.id, camera_id="cam_good", pts_ms=float(n), plate="GJ01GOOD"))
        session.add(VehicleEvent(identity_id=bad_identity.id, camera_id="cam_bad", pts_ms=float(n), plate=None))
    session.commit()

    scores = anpr_suitability_by_camera(session, ["cam_good", "cam_bad", "cam_no_data"])
    assert scores["cam_good"]["classification"] == "CAPABLE"
    assert scores["cam_bad"]["classification"] == "UNSUITABLE"
    assert scores["cam_no_data"]["classification"] == "MARGINAL"
    assert "blur" in scores["cam_good"]["unmeasured_factors"]

    catalogue._cameras = {}
    rows = list_cameras(db=session, principal=Principal("admin", "admin", None))
    by_id = {row["id"]: row for row in rows}
    assert by_id["cam_good"]["anpr_suitability"]["classification"] == "CAPABLE"
    assert by_id["cam_bad"]["anpr_suitability"]["classification"] == "UNSUITABLE"
