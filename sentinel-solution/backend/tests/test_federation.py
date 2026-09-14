"""Regression coverage for Model 3 (VMS Federation & Middleware
Integration) — see docs/models/model-3-vms-federation/. Exercises the
real adapter mapping, idempotent ingest, and correlation-engine logic,
not just a syntax check."""
from __future__ import annotations

import datetime as dt

import pytest

from app.analytics.federation import (
    DemoPartnerVmsAdapter,
    NycOpenDataAdapter,
    SentinelAdapter,
    ingest_all,
)
from app.api.routes_federation import _compute_correlations, _render_correlations_pdf
from app.db.models import CameraRegistry, FederatedEvent, VehicleEvent, VehicleIdentity


def _nyc_csv(tmp_path, rows):
    header = "plate,state,license_type,summons_number,issue_date,violation_time,violation,precinct,county,issuing_agency"
    lines = [header] + [
        f"{plate},NY,PAS,1,{issue_date},{violation_time},SIDEWALK,{precinct},Q,TRAFFIC"
        for plate, issue_date, violation_time, precinct in rows
    ]
    path = tmp_path / "nyc_sample.csv"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_nyc_adapter_parses_split_date_and_12h_time(tmp_path):
    csv_path = _nyc_csv(tmp_path, [("ABC123", "03/15/2023", "01:50P", "108")])
    events = NycOpenDataAdapter(csv_path).fetch_events(dt.datetime(2000, 1, 1))
    assert len(events) == 1
    e = events[0]
    assert e.plate == "ABC123"
    assert e.source_system == "nyc_open_data"
    assert e.camera_id == "precinct-108"
    assert e.observed_at == dt.datetime(2023, 3, 15, 13, 50)  # 01:50P -> 13:50


@pytest.mark.parametrize(
    "raw_time,expected_hour,expected_minute",
    [("12:00A", 0, 0), ("12:00P", 12, 0), ("11:59P", 23, 59), ("01:00A", 1, 0)],
)
def test_nyc_adapter_handles_12h_edge_cases(tmp_path, raw_time, expected_hour, expected_minute):
    """12A/12P are the classic 12-hour-clock off-by-one trap — worth its
    own regression given real government data will contain both."""
    csv_path = _nyc_csv(tmp_path, [("EDGE1", "01/01/2024", raw_time, "001")])
    events = NycOpenDataAdapter(csv_path).fetch_events(dt.datetime(2000, 1, 1))
    assert events[0].observed_at.hour == expected_hour
    assert events[0].observed_at.minute == expected_minute


def test_nyc_adapter_skips_unparseable_rows_instead_of_guessing(tmp_path):
    csv_path = _nyc_csv(tmp_path, [("BAD1", "not-a-date", "01:50P", "108")])
    events = NycOpenDataAdapter(csv_path).fetch_events(dt.datetime(2000, 1, 1))
    assert events == []


def _seed_vehicle_event(session, plate, observed_at, camera_id="cam01"):
    session.add(CameraRegistry(id=camera_id))
    identity = VehicleIdentity(plate=plate)
    session.add(identity)
    session.flush()
    session.add(
        VehicleEvent(
            identity_id=identity.id,
            plate=plate,
            camera_id=camera_id,
            pts_ms=0,
            observed_at=observed_at,
        )
    )
    session.commit()


def test_sentinel_adapter_reads_real_vehicle_events(session):
    _seed_vehicle_event(session, "GJ01RP6128", dt.datetime(2026, 1, 1, 10, 0))
    events = SentinelAdapter(session).fetch_events(dt.datetime(2000, 1, 1))
    assert len(events) == 1
    assert events[0].plate == "GJ01RP6128"
    assert events[0].source_system == "sentinel"


def test_sentinel_adapter_excludes_unread_plates(session):
    """An unread plate (None) must never enter federation — same
    untrusted-input discipline as the rest of the pipeline."""
    session.add(CameraRegistry(id="cam01"))
    identity = VehicleIdentity(plate=None)
    session.add(identity)
    session.flush()
    session.add(VehicleEvent(identity_id=identity.id, plate=None, camera_id="cam01", pts_ms=0))
    session.commit()
    events = SentinelAdapter(session).fetch_events(dt.datetime(2000, 1, 1))
    assert events == []


def test_ingest_all_is_idempotent(session, tmp_path):
    _seed_vehicle_event(session, "GJ01RP6128", dt.datetime(2026, 1, 1, 10, 0))
    csv_path = _nyc_csv(tmp_path, [("ABC123", "01/01/2026", "10:00A", "001")])
    adapters = [SentinelAdapter(session), NycOpenDataAdapter(csv_path)]
    first = ingest_all(session, adapters, dt.datetime(2000, 1, 1))
    second = ingest_all(session, adapters, dt.datetime(2000, 1, 1))
    assert first == 2
    assert second == 0  # re-running must not duplicate rows
    assert session.query(FederatedEvent).count() == 2


def test_correlation_finds_cross_system_match_within_window(session):
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 0), camera_id="cam01"),
        FederatedEvent(source_system="nyc_open_data", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 2), camera_id="precinct-001"),
    ])
    session.commit()
    report = _compute_correlations(session)
    assert report["correlated_plate_count"] == 1
    assert report["correlations"][0]["plate"] == "XYZ999"
    assert report["correlations"][0]["time_gap_s"] == 120
    assert set(report["correlations"][0]["sources"]) == {"sentinel", "nyc_open_data"}


def test_correlation_ignores_matches_outside_window(session):
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 0), camera_id="cam01"),
        FederatedEvent(source_system="nyc_open_data", plate="XYZ999", observed_at=dt.datetime(2026, 1, 2, 10, 0), camera_id="precinct-001"),
    ])
    session.commit()
    report = _compute_correlations(session)
    assert report["correlated_plate_count"] == 0


def test_correlation_ignores_same_source_repeats(session):
    """Two sightings from the SAME source_system must not count as a
    cross-system correlation, even if they share a plate and are close in
    time — this is what makes it federation, not a same-source dedup."""
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 0), camera_id="cam01"),
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 1), camera_id="cam02"),
    ])
    session.commit()
    report = _compute_correlations(session)
    assert report["correlated_plate_count"] == 0


def test_correlation_report_carries_honesty_note(session):
    report = _compute_correlations(session)
    assert "NOT a second Gujarat departmental VMS" in report["honesty_note"]


def test_pdf_export_produces_real_pdf_bytes(session):
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 0), camera_id="cam01"),
        FederatedEvent(source_system="nyc_open_data", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 2), camera_id="precinct-001"),
    ])
    session.commit()
    pdf_bytes = _render_correlations_pdf(_compute_correlations(session))
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_pdf_export_empty_correlations_does_not_crash(session):
    pdf_bytes = _render_correlations_pdf(_compute_correlations(session))
    assert pdf_bytes.startswith(b"%PDF")


def _partner_csv(tmp_path, rows):
    """System C's native format — epoch millis + site_code, deliberately
    different from both other sources."""
    lines = ["vehicle_number,detected_epoch_ms,site_code,device_type"] + [
        f"{plate},{epoch_ms},{site},fixed_anpr" for plate, epoch_ms, site in rows
    ]
    path = tmp_path / "partner_seed.csv"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_partner_adapter_parses_epoch_millis(tmp_path):
    csv_path = _partner_csv(tmp_path, [("GJ01KH0099", 1789003492048, "SITE-AHM-07")])
    events = DemoPartnerVmsAdapter(csv_path).fetch_events(dt.datetime(2000, 1, 1))
    assert len(events) == 1
    e = events[0]
    assert e.plate == "GJ01KH0099"
    assert e.source_system == "demo_partner_vms"
    assert e.camera_id == "SITE-AHM-07"
    assert e.observed_at == dt.datetime(2026, 9, 10, 1, 24, 52, 48000)


def test_partner_adapter_skips_unparseable_epoch_instead_of_guessing(tmp_path):
    csv_path = _partner_csv(tmp_path, [("GJ01KH0099", "not-a-number", "SITE-AHM-07")])
    assert DemoPartnerVmsAdapter(csv_path).fetch_events(dt.datetime(2000, 1, 1)) == []


def test_partner_adapter_respects_the_since_cutoff(tmp_path):
    csv_path = _partner_csv(tmp_path, [("GJ01KH0099", 1789003492048, "SITE-AHM-07")])
    events = DemoPartnerVmsAdapter(csv_path).fetch_events(dt.datetime(2030, 1, 1))
    assert events == []


def test_correlation_flags_a_seeded_match_as_synthetic(session):
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="GJ32B2040", observed_at=dt.datetime(2026, 9, 10, 3, 17, 53), camera_id="cam06"),
        FederatedEvent(source_system="demo_partner_vms", plate="GJ32B2040", observed_at=dt.datetime(2026, 9, 10, 3, 21, 25), camera_id="SITE-VAD-02"),
    ])
    session.commit()
    report = _compute_correlations(session)
    assert report["correlated_plate_count"] == 1
    assert report["correlations"][0]["involves_synthetic_source"] is True


def test_correlation_between_two_real_sources_is_not_flagged_synthetic(session):
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 0), camera_id="cam01"),
        FederatedEvent(source_system="nyc_open_data", plate="XYZ999", observed_at=dt.datetime(2026, 1, 1, 10, 2), camera_id="precinct-001"),
    ])
    session.commit()
    report = _compute_correlations(session)
    assert report["correlations"][0]["involves_synthetic_source"] is False


def test_seeded_event_outside_the_window_does_not_correlate(session):
    """The fixture deliberately includes a +900s sighting so a report proves
    the window gate rejects as well as accepts."""
    session.add_all([
        FederatedEvent(source_system="sentinel", plate="GJ08BF6165", observed_at=dt.datetime(2026, 9, 10, 1, 24, 9), camera_id="cam21"),
        FederatedEvent(source_system="demo_partner_vms", plate="GJ08BF6165", observed_at=dt.datetime(2026, 9, 10, 1, 39, 9), camera_id="SITE-AHM-09"),
    ])
    session.commit()
    assert _compute_correlations(session)["correlated_plate_count"] == 0


def test_shipped_demo_fixture_matches_the_documented_expectations():
    """Guards the checked-in fixture itself: if someone edits the CSV, the
    documented 4-correlate/1-reject outcome must still hold."""
    from app import config

    events = DemoPartnerVmsAdapter(config.DEMO_PARTNER_FIXTURE_PATH).fetch_events(dt.datetime(2000, 1, 1))
    plates = {e.plate for e in events}
    assert plates == {"GJ01KH0099", "GJ09BA7548", "GJ32B2040", "GJ27ED1763", "GJ08BF6165"}
    assert all(e.source_system == "demo_partner_vms" for e in events)
