"""Regression coverage for watchlist/service.py:

1. `add()` upserts — a second `POST /watchlist` for an already-listed
   plate updates the reason instead of raising an IntegrityError.
2. `raise_alert_if_matched()`'s dedup only clears once an alert is
   RESOLVED or DISMISSED, not merely ACKNOWLEDGED — acknowledging doesn't
   let the next track chunk of a still-present vehicle raise a duplicate.
"""
from __future__ import annotations

from app.api.auth import Principal
from app.api.routes_alerts import _apply_status
from app.db.models import (
    ALERT_STATUS_DISMISSED,
    ALERT_STATUS_NEW,
    ALERT_STATUS_RESOLVED,
    Alert,
    CameraRegistry,
    VehicleEvent,
    VehicleIdentity,
)
from app.watchlist.service import WatchlistService


def _seed_event(session):
    camera = session.get(CameraRegistry, "cam01")
    if camera is None:
        camera = CameraRegistry(id="cam01")
        session.add(camera)
        session.commit()
    identity = VehicleIdentity(plate=None)
    session.add(identity)
    session.commit()
    event = VehicleEvent(identity_id=identity.id, camera_id=camera.id, pts_ms=0.0)
    session.add(event)
    session.commit()
    return event


def test_add_upserts_reason_instead_of_raising_on_duplicate_plate(session):
    service = WatchlistService()
    service.add(session, "GJ01AB1234", "stolen")
    service.add(session, "GJ01AB1234", "wanted_person_vehicle")  # must not raise

    from app.db.models import WatchlistEntry

    rows = session.query(WatchlistEntry).filter_by(plate="GJ01AB1234").all()
    assert len(rows) == 1
    assert rows[0].reason == "wanted_person_vehicle"
    assert service.check("GJ01AB1234") == "wanted_person_vehicle"


def test_add_is_case_and_format_normalized_for_upsert(session):
    service = WatchlistService()
    service.add(session, "gj01 ab1234", "stolen")
    service.add(session, "GJ01AB1234", "updated_reason")

    from app.db.models import WatchlistEntry

    assert session.query(WatchlistEntry).count() == 1
    assert service.check("GJ01AB1234") == "updated_reason"


def test_second_sighting_while_alert_still_new_does_not_duplicate(session):
    service = WatchlistService()
    service.add(session, "GJ01AB1234", "stolen")
    event1 = _seed_event(session)
    event2 = _seed_event(session)

    first = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event1.id)
    second = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event2.id)

    assert first is not None
    assert second is None
    assert session.query(Alert).count() == 1


def test_lingering_vehicle_does_not_duplicate_alert_right_after_acknowledge(session):
    """The actual bug: acknowledging an alert ("I've seen this") must not
    immediately reopen the dedup window for the SAME ongoing sighting —
    only resolving/dismissing the case should."""
    service = WatchlistService()
    service.add(session, "GJ01AB1234", "stolen")
    event1 = _seed_event(session)
    event2 = _seed_event(session)

    alert = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event1.id)
    assert alert.status == ALERT_STATUS_NEW

    investigator = Principal("inv1", "investigator", None)
    from app.db.models import ALERT_STATUS_ACKNOWLEDGED

    _apply_status(alert, ALERT_STATUS_ACKNOWLEDGED, investigator)
    session.commit()

    duplicate = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event2.id)

    assert duplicate is None  # the fix: still suppressed, not a new "new" alert
    assert session.query(Alert).count() == 1


def test_new_alert_allowed_after_resolving_the_previous_one(session):
    service = WatchlistService()
    service.add(session, "GJ01AB1234", "stolen")
    event1 = _seed_event(session)
    event2 = _seed_event(session)

    alert = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event1.id)
    investigator = Principal("inv1", "investigator", None)
    from app.db.models import ALERT_STATUS_ACKNOWLEDGED

    _apply_status(alert, ALERT_STATUS_ACKNOWLEDGED, investigator)
    _apply_status(alert, ALERT_STATUS_RESOLVED, investigator)
    session.commit()

    second = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event2.id)

    assert second is not None  # a genuinely new visit after resolution
    assert session.query(Alert).count() == 2


def test_new_alert_allowed_after_dismissing_as_false_positive(session):
    service = WatchlistService()
    service.add(session, "GJ01AB1234", "stolen")
    event1 = _seed_event(session)
    event2 = _seed_event(session)

    alert = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event1.id)
    investigator = Principal("inv1", "investigator", None)
    _apply_status(alert, ALERT_STATUS_DISMISSED, investigator)
    session.commit()

    second = service.raise_alert_if_matched(session, "GJ01AB1234", "cam01", event2.id)

    assert second is not None
    assert session.query(Alert).count() == 2
