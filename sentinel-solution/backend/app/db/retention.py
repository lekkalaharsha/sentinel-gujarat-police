"""Data-retention enforcement — the DPDP "storage limitation" obligation.

Modelled on the UK National ANPR system's enforced retention schedule (see
../../RESEARCH_EXISTING_SYSTEMS.md §6): personal data (vehicle sightings and
the identities built from them) is purged after a bounded window, so the
system doesn't quietly accumulate an indefinite movement database — exactly
the oversight gap the UK system was criticized for lacking.

Design decisions, stated honestly:
- Vehicle events, their now-orphaned identities, and old alerts are purged
  after RETENTION_DAYS.
- Audit logs are kept LONGER (AUDIT_RETENTION_DAYS) — the record of WHO
  queried WHAT should outlive the data itself, or the accountability trail
  is useless. This is a deliberate asymmetry, not an oversight.
- This is time-based purge only. A production system would also exempt data
  flagged to an active case (CPIA-style evidential retention in the UK
  model) — we don't have per-event case-flagging yet, so that exemption is
  a documented gap, NOT silently pretended-implemented. Purge is
  conservative-by-omission: it deletes on schedule regardless, so nothing
  is retained beyond policy, but an operator must export evidence to a case
  file before it ages out. Flagged as future work.
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from .models import Alert, AuditLog, VehicleEvent, VehicleIdentity

logger = logging.getLogger("sentinel.retention")


def purge_expired(session: Session, now: dt.datetime | None = None) -> dict:
    """Delete data older than the configured retention windows. Returns a
    count summary. Safe to call repeatedly (idempotent — nothing to delete
    on a second run)."""
    now = now or dt.datetime.utcnow()
    event_cutoff = now - dt.timedelta(days=config.RETENTION_DAYS)
    audit_cutoff = now - dt.timedelta(days=config.AUDIT_RETENTION_DAYS)

    # Alerts reference vehicle events (FK), so delete alerts for expired
    # events first to avoid dangling references.
    expired_event_ids = [
        row[0] for row in session.execute(
            select(VehicleEvent.id).where(VehicleEvent.observed_at < event_cutoff)
        )
    ]
    alerts_deleted = 0
    if expired_event_ids:
        alerts_deleted = (
            session.query(Alert)
            .filter(Alert.vehicle_event_id.in_(expired_event_ids))
            .delete(synchronize_session=False)
        )
    # Also purge old alerts whose event may already be gone.
    alerts_deleted += (
        session.query(Alert).filter(Alert.created_at < event_cutoff).delete(synchronize_session=False)
    )

    events_deleted = (
        session.query(VehicleEvent)
        .filter(VehicleEvent.observed_at < event_cutoff)
        .delete(synchronize_session=False)
    )

    # Identities with no remaining events are now orphaned personal data —
    # purge them too (subquery: identities not referenced by any event).
    referenced = select(VehicleEvent.identity_id).distinct()
    identities_deleted = (
        session.query(VehicleIdentity)
        .filter(VehicleIdentity.id.notin_(referenced))
        .filter(VehicleIdentity.last_seen_at < event_cutoff)
        .delete(synchronize_session=False)
    )

    audit_deleted = (
        session.query(AuditLog)
        .filter(AuditLog.created_at < audit_cutoff)
        .delete(synchronize_session=False)
    )

    session.commit()
    summary = {
        "events_deleted": events_deleted,
        "identities_deleted": identities_deleted,
        "alerts_deleted": alerts_deleted,
        "audit_logs_deleted": audit_deleted,
        "event_cutoff": event_cutoff.isoformat(),
        "audit_cutoff": audit_cutoff.isoformat(),
    }
    if events_deleted or identities_deleted or alerts_deleted or audit_deleted:
        logger.info("retention purge: %s", summary)
    return summary
