"""Regression coverage for routes_vehicle.py's search_by_attributes
truncation. Confirmed 2026-09-10 (P1 re-research pass) that the endpoint
hard-limited to 200 results ordered oldest-first with no total-count/
truncated signal — silently dropping the most RECENT matches with no way
for a caller to know results were cut off. This locks in the fix: desc()
ordering + total_count/truncated in the response."""
from __future__ import annotations

import datetime as dt

from app.api.auth import Principal
from app.api.routes_vehicle import search_by_attributes
from app.db.models import CameraRegistry, VehicleEvent, VehicleIdentity


def _seed_events(session, count, vehicle_type="car"):
    camera = CameraRegistry(id="cam01")
    identity = VehicleIdentity(plate=None)
    session.add(camera)
    session.add(identity)
    session.commit()
    base = dt.datetime(2026, 1, 1)
    for i in range(count):
        session.add(
            VehicleEvent(
                identity_id=identity.id,
                camera_id=camera.id,
                pts_ms=float(i),
                observed_at=base + dt.timedelta(minutes=i),
                vehicle_type=vehicle_type,
            )
        )
    session.commit()


def test_no_truncation_under_200_results(session):
    _seed_events(session, 5)
    investigator = Principal("inv1", "investigator", None)
    result = search_by_attributes(purpose="stolen_vehicle_investigation", vehicle_type=None,
                                   color=None, partial_plate=None, case_id=None,
                                   db=session, principal=investigator)
    assert result["total_count"] == 5
    assert result["truncated"] is False
    assert len(result["matches"]) == 5


def test_truncation_signalled_and_returns_most_recent(session):
    _seed_events(session, 210)
    investigator = Principal("inv1", "investigator", None)
    result = search_by_attributes(purpose="stolen_vehicle_investigation", vehicle_type=None,
                                   color=None, partial_plate=None, case_id=None,
                                   db=session, principal=investigator)
    assert result["total_count"] == 210
    assert result["truncated"] is True
    assert len(result["matches"]) == 200
    # desc() ordering: the most recent 200 of 210 survive, not the oldest 200.
    observed_ats = [m["observed_at"] for m in result["matches"]]
    assert observed_ats == sorted(observed_ats, reverse=True)
    newest_expected = (dt.datetime(2026, 1, 1) + dt.timedelta(minutes=209)).isoformat()
    assert result["matches"][0]["observed_at"] == newest_expected
