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
from ..db.models import Alert, WatchlistEntry

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
        plate = normalize_plate(plate)
        entry = WatchlistEntry(plate=plate, reason=reason)
        session.add(entry)
        session.commit()
        with self._lock:
            self._plates[plate] = reason

    def check(self, plate: str) -> Optional[str]:
        with self._lock:
            return self._plates.get(normalize_plate(plate))

    def raise_alert_if_matched(
        self, session: Session, plate: str, camera_id: str, vehicle_event_id: int
    ) -> Optional[Alert]:
        reason = self.check(plate)
        if reason is None:
            return None
        alert = Alert(
            plate=normalize_plate(plate),
            camera_id=camera_id,
            reason=reason,
            vehicle_event_id=vehicle_event_id,
        )
        session.add(alert)
        session.commit()
        logger.warning("ALERT: plate=%s camera=%s reason=%s", plate, camera_id, reason)
        return alert


watchlist_service = WatchlistService()
