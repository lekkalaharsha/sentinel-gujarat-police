"""Named anomaly alerts — wrong-way vehicle / stopped-in-restricted-zone.

Deliberately narrow, per STRATEGY.md's OUT list ("generic/unscoped anomaly
detection... replace with named, measurable events if time allows"): no
"anomaly score", no ML model, just two named conditions checked against
motion attributes the pipeline already computes for every finalized track
(`VehicleEvent.dwell_time_s`/`speed_px_per_s`/`direction_deg`, see
`db/models.py`'s docstring on why these are image-plane, not physical,
units). Both conditions are opt-in per camera (`CameraRegistry.
is_restricted_zone`/`expected_direction_deg`) — a camera with neither
configured never produces an anomaly alert.
"""
from __future__ import annotations

import logging
from typing import List, NamedTuple, Optional

from sqlalchemy.orm import Session

from .. import config
from ..db.models import ALERT_STATUS_NEW, Alert, CameraRegistry, VehicleEvent, VehicleIdentity

logger = logging.getLogger("sentinel.anomaly")

ALERT_TYPE_WRONG_WAY = "wrong_way"
ALERT_TYPE_STOPPED_ZONE = "stopped_restricted_zone"


class AnomalyHit(NamedTuple):
    alert_type: str
    reason: str


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest absolute difference between two directions on a circle
    (e.g. 350 vs 10 is a 20-degree difference, not 340)."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def detect_anomalies(camera: Optional[CameraRegistry], event: VehicleEvent) -> List[AnomalyHit]:
    """Pure function, no DB/session access — takes the already-finalized
    event + its camera row, returns anomaly types triggered. Called once
    per finalized track (see pipeline.py), same cardinality as the
    watchlist check, so no extra per-frame overhead."""
    hits: List[AnomalyHit] = []
    if camera is None:
        return hits

    if (
        camera.is_restricted_zone
        and event.dwell_time_s is not None
        and event.dwell_time_s >= config.STOPPED_ZONE_DWELL_THRESHOLD_S
    ):
        hits.append(AnomalyHit(
            ALERT_TYPE_STOPPED_ZONE,
            f"vehicle stationary for {event.dwell_time_s:.0f}s in a restricted zone",
        ))

    if (
        camera.expected_direction_deg is not None
        and event.direction_deg is not None
        and event.speed_px_per_s is not None
        and event.speed_px_per_s >= config.WRONG_WAY_MIN_SPEED_PX_S
    ):
        diff = _angle_diff_deg(event.direction_deg, camera.expected_direction_deg)
        if diff >= config.WRONG_WAY_ANGLE_THRESHOLD_DEG:
            hits.append(AnomalyHit(
                ALERT_TYPE_WRONG_WAY,
                f"vehicle moving {diff:.0f}° against the expected direction of travel",
            ))

    return hits


def raise_anomaly_alerts(
    session: Session,
    camera: Optional[CameraRegistry],
    event: VehicleEvent,
    identity: VehicleIdentity,
) -> List[Alert]:
    """Persists an Alert per anomaly hit, same dedup rule as the watchlist
    path (one open alert per (alert_type, camera, vehicle) at a time — see
    WatchlistService.raise_alert_if_matched's comment for why). `plate` is
    NOT NULL on Alert (original design assumed a watchlist match, which
    always has one) — an anomaly can trigger on a vehicle whose plate was
    never read at this camera, so we fall back to an identity-scoped
    placeholder rather than requiring a plate the anomaly logic can't
    guarantee (see db/models.py's Alert.plate docstring)."""
    hits = detect_anomalies(camera, event)
    if not hits:
        return []

    plate_label = identity.plate or f"UNREAD#{identity.id}"
    raised: List[Alert] = []
    for hit in hits:
        existing_open = (
            session.query(Alert)
            .filter_by(plate=plate_label, camera_id=event.camera_id, alert_type=hit.alert_type)
            .filter(Alert.status == ALERT_STATUS_NEW)
            .first()
        )
        if existing_open is not None:
            continue
        alert = Alert(
            plate=plate_label,
            camera_id=event.camera_id,
            reason=hit.reason,
            alert_type=hit.alert_type,
            vehicle_event_id=event.id,
        )
        session.add(alert)
        raised.append(alert)
        logger.warning(
            "ANOMALY ALERT: type=%s plate=%s camera=%s reason=%s",
            hit.alert_type, plate_label, event.camera_id, hit.reason,
        )
    if raised:
        session.commit()
    return raised
