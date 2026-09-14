"""Model 4 pilot density aggregation over real detector outputs.

This is deliberately an aggregate of sampled-frame detections, not a crowd
estimator and not an alerting system.  It needs no new model or infrastructure.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .. import config
from ..db.models import CameraDensityWindow


@dataclass
class PendingDensity:
    camera_id: str
    window_started_at: dt.datetime
    window_seconds: int
    sampled_frames: int = 0
    vehicle_detections: int = 0
    person_detections: int = 0
    updated_at: dt.datetime | None = None


class DensityBatcher:
    """In-memory per-camera aggregation; writes occur once per time window."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingDensity] = {}

    def add(self, camera_id: str, observed_at: dt.datetime, detections: list) -> PendingDensity | None:
        window_s = config.ANALYTICS_DENSITY_WINDOW_S
        epoch_s = int(observed_at.timestamp())
        started_at = dt.datetime.utcfromtimestamp(epoch_s - (epoch_s % window_s))
        current = self._pending.get(camera_id)
        flushed = current if current and current.window_started_at != started_at else None
        if flushed:
            self._pending.pop(camera_id)
            current = None
        if current is None:
            current = PendingDensity(camera_id, started_at, window_s)
            self._pending[camera_id] = current
        current.sampled_frames += 1
        current.vehicle_detections += sum(1 for detection in detections if detection.label != "person")
        current.person_detections += sum(1 for detection in detections if detection.label == "person")
        current.updated_at = observed_at
        return flushed

    def flush_camera(self, camera_id: str) -> PendingDensity | None:
        return self._pending.pop(camera_id, None)


def record_detection_counts(
    session: Session, camera_id: str, observed_at: dt.datetime, detections: list,
) -> CameraDensityWindow:
    window_s = config.ANALYTICS_DENSITY_WINDOW_S
    epoch_s = int(observed_at.timestamp())
    bucket_s = epoch_s - (epoch_s % window_s)
    window_started_at = dt.datetime.utcfromtimestamp(bucket_s)
    row = (
        session.query(CameraDensityWindow)
        .filter_by(camera_id=camera_id, window_started_at=window_started_at, window_seconds=window_s)
        .first()
    )
    if row is None:
        row = CameraDensityWindow(
            camera_id=camera_id, window_started_at=window_started_at, window_seconds=window_s,
            sampled_frames=0, vehicle_detections=0, person_detections=0,
        )
        session.add(row)
    row.sampled_frames += 1
    row.vehicle_detections += sum(1 for detection in detections if detection.label != "person")
    row.person_detections += sum(1 for detection in detections if detection.label == "person")
    row.updated_at = observed_at
    return row


def record_batched_counts(session: Session, batch: PendingDensity) -> CameraDensityWindow:
    row = (
        session.query(CameraDensityWindow)
        .filter_by(camera_id=batch.camera_id, window_started_at=batch.window_started_at, window_seconds=batch.window_seconds)
        .first()
    )
    if row is None:
        row = CameraDensityWindow(
            camera_id=batch.camera_id, window_started_at=batch.window_started_at, window_seconds=batch.window_seconds,
            sampled_frames=0, vehicle_detections=0, person_detections=0,
        )
        session.add(row)
    row.sampled_frames += batch.sampled_frames
    row.vehicle_detections += batch.vehicle_detections
    row.person_detections += batch.person_detections
    row.updated_at = batch.updated_at
    return row


def storage_tier_for(observed_at: dt.datetime, now: dt.datetime | None = None) -> str:
    """Classify age for display only; no storage backend is selected here."""
    now = now or dt.datetime.utcnow()
    age_days = max(0.0, (now - observed_at).total_seconds() / 86400)
    if age_days <= config.STORAGE_HOT_DAYS:
        return "hot"
    if age_days <= config.STORAGE_WARM_DAYS:
        return "warm"
    return "cold"
