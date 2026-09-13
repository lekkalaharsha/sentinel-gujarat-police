"""Model 4 pilot density aggregation over real detector outputs.

This is deliberately an aggregate of sampled-frame detections, not a crowd
estimator and not an alerting system.  It needs no new model or infrastructure.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .. import config
from ..db.models import CameraDensityWindow


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


def storage_tier_for(observed_at: dt.datetime, now: dt.datetime | None = None) -> str:
    """Classify age for display only; no storage backend is selected here."""
    now = now or dt.datetime.utcnow()
    age_days = max(0.0, (now - observed_at).total_seconds() / 86400)
    if age_days <= config.STORAGE_HOT_DAYS:
        return "hot"
    if age_days <= config.STORAGE_WARM_DAYS:
        return "warm"
    return "cold"
