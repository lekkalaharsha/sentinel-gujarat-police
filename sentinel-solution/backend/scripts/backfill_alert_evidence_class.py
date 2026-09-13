"""One-time (idempotent) backfill: populate Alert.evidence_class /
evidence_class_reason for alerts created before those columns existed.

Also the remediation for the real bug found 2026-09-13 (independent review +
DECISION_REVIEW_2026-09-11.md): pipeline.py used to gate watchlist alerts on
`identity.plate` instead of the triggering event's OWN plate/link_method, so
a LEAD_ONLY appearance-match sighting could raise an ordinary plate-matched
alert if the identity had been plate-confirmed by a DIFFERENT, earlier
sighting. Fixed in analytics/pipeline.py (now gates on
`evidence_class.classify(event.plate, event.link_method) == CONFIRMED`).

This script does NOT change any alert's status (new/acknowledged/resolved/
dismissed) — that would rewrite a real investigator decision, which
CLAUDE.md's evidence-append-only rule forbids. It only backfills the new
evidence_class/evidence_class_reason columns from each alert's already-
persisted triggering event, so the historical record correctly shows which
past alerts were policy violations rather than silently leaving them
unlabeled. Safe to re-run: only touches rows where evidence_class IS NULL.
"""
from __future__ import annotations

import logging

from app.analytics import evidence_class as evclass
from app.db.models import Alert, VehicleEvent
from app.db.session import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel.backfill_alert_evidence_class")


def run() -> None:
    init_db()
    session = SessionLocal()
    try:
        alerts = (
            session.query(Alert, VehicleEvent)
            .join(VehicleEvent, VehicleEvent.id == Alert.vehicle_event_id)
            .filter(Alert.evidence_class.is_(None))
            .all()
        )
        updated = 0
        violations = 0
        for alert, event in alerts:
            sighting_class = evclass.classify(event.plate, event.link_method)
            reason = evclass.describe(sighting_class, event.link_method)
            is_watchlist = (alert.alert_type or "watchlist") == "watchlist"
            if is_watchlist and sighting_class != evclass.CONFIRMED:
                # A watchlist (plate-match) alert whose OWN triggering event
                # never read a plate — exactly the pre-fix policy violation.
                reason = (
                    f"POLICY VIOLATION (pre-fix, found 2026-09-13): this watchlist "
                    f"alert was raised from a {sighting_class} sighting, not a "
                    f"validated plate read at this camera. {reason}"
                )
                violations += 1
                logger.warning(
                    "alert id=%s plate=%s camera=%s: pre-fix policy violation, "
                    "underlying event id=%s is %s (link_method=%s)",
                    alert.id, alert.plate, alert.camera_id, event.id, sighting_class, event.link_method,
                )
            alert.evidence_class = sighting_class
            alert.evidence_class_reason = reason
            updated += 1
        session.commit()
        logger.info("backfilled %d alert(s), %d flagged as pre-fix policy violations", updated, violations)
    finally:
        session.close()


if __name__ == "__main__":
    run()
