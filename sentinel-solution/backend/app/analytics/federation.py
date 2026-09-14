"""Model 3 — VMS Federation & Middleware Integration: adapter layer.

Two independently-formatted, real event sources normalized into one shape
so a downstream correlation engine (see `routes_federation.py`) doesn't
need to know each source's native schema. Same `Protocol`-based stub/real
pattern as `analytics/detector.py`'s `VehicleDetector` — adding a third
source later means writing one more `VMSAdapter` implementation, no
change to anything downstream.

System A (`SentinelAdapter`) wraps Sentinel's own real, already-built
Model 1/2 stack — no new ingestion, just a read of `VehicleEvent`.

System B (`NycOpenDataAdapter`) is NOT a second Gujarat departmental VMS —
there isn't one available to federate against. It's a real, independent,
public dataset (NYC Open Data's "Open Parking and Camera Violations",
see `scripts/fixtures/nyc_open_parking_sample.README.md` for provenance),
used to demonstrate genuine format-heterogeneity handling (different
field names, a split date+time representation, a precinct/county location
model instead of lat/lon+camera_id, a different plate-format convention).
There is zero real plate overlap between this dataset and the Gujarat
sandbox by construction (different countries) — see
`docs/models/model-3-vms-federation/ARCHITECTURE.md`'s honesty caveat.
Never present `source_system="nyc_open_data"` output as a Gujarat
departmental system in any UI/report built on this module.

System C (`DemoPartnerVmsAdapter`) is SYNTHETIC and exists only so the
correlation engine can be exercised end-to-end: because A and B share no
plates, a live run would otherwise always return zero correlations and the
join path would be proven by unit tests alone. Its `source_system` is
`demo_partner_vms` precisely so it is self-labelling wherever it surfaces.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from sqlalchemy.orm import Session

from ..db.models import FederatedEvent, VehicleEvent

SOURCE_SENTINEL = "sentinel"
SOURCE_NYC_OPEN_DATA = "nyc_open_data"
# Synthetic. See `DemoPartnerVmsAdapter` and the fixture's README — this id is
# deliberately self-describing so it can never read as a real agency feed.
SOURCE_DEMO_PARTNER_VMS = "demo_partner_vms"


@dataclass
class NormalizedEvent:
    plate: str
    observed_at: dt.datetime
    camera_id: str  # source-native location identifier — a real camera id for
                     # "sentinel", a precinct/county code for "nyc_open_data"
    source_system: str
    raw_payload: dict = field(default_factory=dict)


class VMSAdapter(Protocol):
    def fetch_events(self, since: dt.datetime) -> List[NormalizedEvent]: ...


class SentinelAdapter:
    """Real System A. Reads `VehicleEvent` rows Model 2 already collects —
    no new ingestion, this is a normalization view over existing data."""

    def __init__(self, db: Session):
        self._db = db

    def fetch_events(self, since: dt.datetime) -> List[NormalizedEvent]:
        rows = (
            self._db.query(VehicleEvent)
            .filter(VehicleEvent.observed_at >= since)
            .filter(VehicleEvent.plate.isnot(None))
            .all()
        )
        return [
            NormalizedEvent(
                plate=row.plate,
                observed_at=row.observed_at,
                camera_id=row.camera_id,
                source_system=SOURCE_SENTINEL,
                raw_payload={"vehicle_event_id": row.id, "confidence": row.plate_confidence},
            )
            for row in rows
        ]


class NycOpenDataAdapter:
    """Real System B — see this module's docstring for the honesty caveat.
    Parses NYC Open Data's native format (split `issue_date`+
    `violation_time` in `MM/DD/YYYY`+`HH:MMA/P` form, a `precinct` location
    code instead of a camera id) into the same `NormalizedEvent` shape
    `SentinelAdapter` produces — this mapping IS the "adapter/plugin
    architecture for multiple vendors" deliverable in miniature."""

    def __init__(self, csv_path: str):
        self._csv_path = csv_path

    def fetch_events(self, since: dt.datetime) -> List[NormalizedEvent]:
        out: List[NormalizedEvent] = []
        with open(self._csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                observed_at = self._parse_timestamp(row.get("issue_date"), row.get("violation_time"))
                if observed_at is None or observed_at < since:
                    continue
                plate = (row.get("plate") or "").strip()
                if not plate:
                    continue
                out.append(
                    NormalizedEvent(
                        plate=plate,
                        observed_at=observed_at,
                        camera_id=f"precinct-{row.get('precinct', 'unknown')}",
                        source_system=SOURCE_NYC_OPEN_DATA,
                        raw_payload=dict(row),
                    )
                )
        return out

    @staticmethod
    def _parse_timestamp(issue_date: Optional[str], violation_time: Optional[str]) -> Optional[dt.datetime]:
        """NYC's native format splits date and time into separate fields
        with a 12-hour+AM/PM-suffix time (e.g. "03/15/2023" + "01:50P") —
        deliberately different from Sentinel's single ISO `observed_at`
        column. Returns None for rows with an unparseable/missing
        timestamp rather than guessing — a federation adapter must not
        silently fabricate a time for real third-party data."""
        if not issue_date or not violation_time:
            return None
        try:
            date_part = dt.datetime.strptime(issue_date.strip(), "%m/%d/%Y")
        except ValueError:
            return None
        raw_time = violation_time.strip().upper()
        if not raw_time or raw_time[-1] not in ("A", "P"):
            return None
        suffix = raw_time[-1]
        try:
            hour, minute = (int(p) for p in raw_time[:-1].split(":"))
        except ValueError:
            return None
        if suffix == "P" and hour != 12:
            hour += 12
        if suffix == "A" and hour == 12:
            hour = 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return date_part.replace(hour=hour, minute=minute)


class DemoPartnerVmsAdapter:
    """SYNTHETIC source — every row it returns was hand-written, not observed.

    The two real sources have zero plate overlap (different countries, three
    years apart), so the correlation engine could only ever be exercised by
    unit tests against synthetic rows, never end-to-end against the live
    database. This adapter closes that gap by replaying hand-written partner
    sightings of plates Sentinel really did read, offset by a known number of
    seconds — including one deliberately outside the correlation window so a
    report proves the gate rejects as well as accepts.

    Its native format is a third schema again (`vehicle_number`, epoch
    milliseconds, `site_code`), so the adapter layer is exercised against
    three genuinely different shapes rather than two.

    `source_system` is `demo_partner_vms` so no response, dashboard or PDF can
    present it as a real departmental feed. See
    `scripts/fixtures/demo_partner_vms_seed.README.md`.
    """

    def __init__(self, csv_path: str):
        self._csv_path = csv_path

    def fetch_events(self, since: dt.datetime) -> List[NormalizedEvent]:
        out: List[NormalizedEvent] = []
        with open(self._csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                observed_at = self._parse_epoch_ms(row.get("detected_epoch_ms"))
                if observed_at is None or observed_at < since:
                    continue
                plate = (row.get("vehicle_number") or "").strip()
                if not plate:
                    continue
                out.append(
                    NormalizedEvent(
                        plate=plate,
                        observed_at=observed_at,
                        camera_id=(row.get("site_code") or "unknown").strip(),
                        source_system=SOURCE_DEMO_PARTNER_VMS,
                        raw_payload=dict(row),
                    )
                )
        return out

    @staticmethod
    def _parse_epoch_ms(raw: Optional[str]) -> Optional[dt.datetime]:
        """Epoch milliseconds (UTC) -> the naive-UTC datetime the rest of the
        pipeline uses. Returns None rather than guessing on a bad value, same
        discipline as the NYC adapter's timestamp parser."""
        if not raw:
            return None
        try:
            return dt.datetime.utcfromtimestamp(int(raw.strip()) / 1000.0)
        except (ValueError, OverflowError, OSError):
            return None


def ingest_all(db: Session, adapters: List[VMSAdapter], since: dt.datetime) -> int:
    """Pull from every adapter and land new events into `FederatedEvent` —
    the polled "metadata exchange bus" (deliberately not Kafka, see
    docs/models/model-3-vms-federation/RESEARCH.md). Idempotent: skips any
    (source_system, plate, observed_at, camera_id) tuple already present,
    so repeated polls over overlapping windows don't create duplicate rows.
    Returns the number of new rows inserted."""
    existing = {
        (row.source_system, row.plate, row.observed_at, row.camera_id)
        for row in db.query(
            FederatedEvent.source_system, FederatedEvent.plate, FederatedEvent.observed_at, FederatedEvent.camera_id
        )
    }
    inserted = 0
    for adapter in adapters:
        for event in adapter.fetch_events(since):
            key = (event.source_system, event.plate, event.observed_at, event.camera_id)
            if key in existing:
                continue
            existing.add(key)
            db.add(
                FederatedEvent(
                    source_system=event.source_system,
                    plate=event.plate,
                    observed_at=event.observed_at,
                    camera_id=event.camera_id,
                    raw_payload_json=json.dumps(event.raw_payload, default=str),
                )
            )
            inserted += 1
    db.commit()
    return inserted
