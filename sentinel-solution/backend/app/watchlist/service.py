"""Watchlist cross-referencing and alert generation.

Kept as a thin, in-process cache over the DB table so the hot path (every
ANPR read) doesn't hit the DB per lookup — refreshed on writes.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, Optional

from sqlalchemy.orm import Session

from ..analytics.anpr import normalize_plate
from ..db.models import ALERT_STATUS_ACKNOWLEDGED, ALERT_STATUS_NEW, Alert, WatchlistEntry

logger = logging.getLogger("sentinel.watchlist")


class WatchlistService:
    def __init__(self):
        self._lock = threading.RLock()
        self._plates: Dict[str, str] = {}  # plate -> reason

    def load(self, session: Session) -> None:
        with self._lock:
            self._plates = {
                e.plate: e.reason for e in session.query(WatchlistEntry).all()
            }
        logger.info("watchlist loaded: %d entries", len(self._plates))

    def add(self, session: Session, plate: str, reason: str) -> None:
        """Upsert: `WatchlistEntry.plate` is unique, so re-adding an
        already-listed plate updates its reason instead of raising."""
        plate = normalize_plate(plate)
        existing = session.query(WatchlistEntry).filter_by(plate=plate).first()
        if existing is not None:
            existing.reason = reason
        else:
            session.add(WatchlistEntry(plate=plate, reason=reason))
        session.commit()
        with self._lock:
            self._plates[plate] = reason

    def check(self, plate: str) -> Optional[str]:
        with self._lock:
            return self._plates.get(normalize_plate(plate))

    def raise_alert_if_matched(
        self,
        session: Session,
        plate: str,
        camera_id: str,
        vehicle_event_id: int,
        evidence_class: Optional[str] = None,
        evidence_class_reason: Optional[str] = None,
    ) -> Optional[Alert]:
        reason = self.check(plate)
        if reason is None:
            return None
        # A vehicle lingering in one camera's view is processed as several
        # short tracks/sightings (temporal fusion finalizes on any gap, see
        # tracker.py), each independently re-matching the watchlist. Only
        # RESOLVED/DISMISSED clears the dedup window — NEW or ACKNOWLEDGED
        # still counts as open, since acknowledging ("I've seen this") isn't
        # the same as the case being closed and shouldn't let the very next
        # track chunk of the same still-present vehicle raise a duplicate.
        existing_open = (
            session.query(Alert)
            .filter_by(plate=normalize_plate(plate), camera_id=camera_id)
            .filter(Alert.status.in_([ALERT_STATUS_NEW, ALERT_STATUS_ACKNOWLEDGED]))
            .first()
        )
        if existing_open is not None:
            return None
        alert = Alert(
            plate=normalize_plate(plate),
            camera_id=camera_id,
            reason=reason,
            vehicle_event_id=vehicle_event_id,
            evidence_class=evidence_class,
            evidence_class_reason=evidence_class_reason,
        )
        session.add(alert)
        session.commit()
        logger.warning("ALERT: plate=%s camera=%s reason=%s", plate, camera_id, reason)
        return alert


watchlist_service = WatchlistService()
