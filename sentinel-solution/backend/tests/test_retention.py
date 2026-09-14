"""Regression coverage for db/retention.py's purge job: crop image files
on disk (config.CROPS_DIR) must be deleted alongside their VehicleEvent
row's purge, best-effort, only after the DB commit succeeds.
"""
from __future__ import annotations

import datetime as dt
import os

from app.db.models import CameraRegistry, VehicleEvent, VehicleIdentity
from app.db.retention import purge_expired


def _seed_event(session, tmp_path, *, observed_at, with_crop=True, crop_exists=True):
    camera = CameraRegistry(id="cam01")
    identity = VehicleIdentity(plate=None)
    session.add(camera)
    session.add(identity)
    session.commit()

    crop_path = None
    if with_crop:
        crop_path = str(tmp_path / "crop.jpg")
        if crop_exists:
            with open(crop_path, "wb") as f:
                f.write(b"fake-jpeg-bytes")

    event = VehicleEvent(
        identity_id=identity.id,
        camera_id=camera.id,
        pts_ms=0.0,
        observed_at=observed_at,
        crop_path=crop_path,
    )
    session.add(event)
    session.commit()
    return event, crop_path


def test_purge_deletes_expired_crop_file_from_disk(session, tmp_path):
    old = dt.datetime.utcnow() - dt.timedelta(days=365)
    _event, crop_path = _seed_event(session, tmp_path, observed_at=old)
    assert os.path.exists(crop_path)

    summary = purge_expired(session)

    assert summary["events_deleted"] == 1
    assert summary["crop_files_deleted"] == 1
    assert not os.path.exists(crop_path)


def test_purge_does_not_touch_crop_file_for_a_non_expired_event(session, tmp_path):
    fresh = dt.datetime.utcnow()
    _event, crop_path = _seed_event(session, tmp_path, observed_at=fresh)
    assert os.path.exists(crop_path)

    summary = purge_expired(session)

    assert summary["events_deleted"] == 0
    assert summary["crop_files_deleted"] == 0
    assert os.path.exists(crop_path)


def test_purge_survives_an_already_missing_crop_file(session, tmp_path):
    """A row whose crop was deleted out-of-band, or never saved to begin
    with, must not abort the purge — best-effort cleanup only."""
    old = dt.datetime.utcnow() - dt.timedelta(days=365)
    _event, crop_path = _seed_event(session, tmp_path, observed_at=old, crop_exists=False)
    assert not os.path.exists(crop_path)

    summary = purge_expired(session)

    assert summary["events_deleted"] == 1
    assert summary["crop_files_deleted"] == 0  # nothing there to delete, not an error


def test_purge_of_event_with_no_crop_path_is_a_noop_for_files(session, tmp_path):
    old = dt.datetime.utcnow() - dt.timedelta(days=365)
    _event, _crop_path = _seed_event(session, tmp_path, observed_at=old, with_crop=False)

    summary = purge_expired(session)

    assert summary["events_deleted"] == 1
    assert summary["crop_files_deleted"] == 0
