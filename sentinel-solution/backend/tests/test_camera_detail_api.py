from __future__ import annotations

import datetime as dt

import pytest
from fastapi import HTTPException

from app.api.auth import Principal
from app.api.routes_alerts import list_alerts
from app.api.routes_cameras import camera_stats
from app.api.routes_vehicle import recent_detections
from app.db.models import Alert, CameraRegistry, VehicleEvent, VehicleIdentity


def _event(session, camera_id: str, observed_at: dt.datetime, plate=None, link_method=None):
    identity = VehicleIdentity(plate=plate)
    session.add(identity)
    session.flush()
    session.add(VehicleEvent(identity_id=identity.id, camera_id=camera_id, pts_ms=1, observed_at=observed_at, plate=plate, link_method=link_method))


def test_camera_filters_and_stats_are_scoped_and_classified(session):
    session.add_all([CameraRegistry(id="police", department="Police"), CameraRegistry(id="health", department="Health")])
    now = dt.datetime.utcnow()
    _event(session, "police", now, plate="GJ01AB1234")
    _event(session, "police", now - dt.timedelta(minutes=1), link_method="plate_continuation")
    _event(session, "police", now - dt.timedelta(minutes=2), link_method="appearance_match")
    _event(session, "police", now - dt.timedelta(hours=25), plate="GJ01OLD01")
    _event(session, "health", now, plate="GJ02ZZ9999")
    session.commit()

    police = Principal("police-investigator", "investigator", "Police")
    recent = recent_detections(limit=20, camera_id="police", db=session, principal=police)
    assert len(recent) == 4
    assert {item["camera_id"] for item in recent} == {"police"}
    assert recent_detections(limit=20, camera_id="health", db=session, principal=police) == []

    stats = camera_stats("police", db=session, principal=Principal("police-viewer", "viewer", "Police"))
    assert stats["window_hours"] == 24
    assert stats["sighting_count"] == 3
    assert stats["by_evidence_class"] == {"CONFIRMED": 1, "PROBABLE": 1, "LEAD_ONLY": 1}
    with pytest.raises(HTTPException) as exc_info:
        camera_stats("health", db=session, principal=Principal("police-viewer", "viewer", "Police"))
    assert exc_info.value.status_code == 404


def test_alert_camera_filter_composes_with_department_scope(session):
    session.add_all([CameraRegistry(id="police", department="Police"), CameraRegistry(id="health", department="Health")])
    identity = VehicleIdentity(plate="GJ01AB1234")
    session.add(identity)
    session.flush()
    event = VehicleEvent(identity_id=identity.id, camera_id="police", pts_ms=1)
    session.add(event)
    session.flush()
    session.add_all([
        Alert(plate="GJ01AB1234", camera_id="police", reason="stolen", vehicle_event_id=event.id),
        Alert(plate="GJ02ZZ9999", camera_id="health", reason="wanted", vehicle_event_id=event.id),
    ])
    session.commit()

    police = Principal("police-investigator", "investigator", "Police")
    assert [alert["camera_id"] for alert in list_alerts(db=session, camera_id="police", principal=police)] == ["police"]
    assert list_alerts(db=session, camera_id="health", principal=police) == []
