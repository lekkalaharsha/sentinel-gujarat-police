"""Regression tests for analytics/identity.py (SWE-4).

Guards the geo-feasibility gate added 2026-09-04 after an appearance-only
identity drifted across ~100 unrelated real vehicles statewide in 15 minutes
(see identity.py's module docstring and REVIEW_FINDINGS.md). The four
behaviors under test:

(a) an appearance-only match that is geo-infeasible is rejected into a NEW
    identity — the drift fix;
(b) a geo-feasible appearance match links to the existing identity;
(c) a direct plate re-read always continues the existing identity,
    regardless of geo-feasibility — plate is strong ground truth, the gate
    only ever applies to appearance-only evidence;
(d) the plate-upgrade path (anonymous identity later gets a plate read)
    retro-links: the same identity row keeps its id, so earlier anonymous
    sightings stay attached.

Plus guardrails: the 60-minute association window, the 0.80 similarity
floor, missing-GPS "can't assess -> don't block" semantics, and anonymous
continuation of an already-plated identity.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from app.analytics.identity import ASSOCIATION_WINDOW, IdentityResolver
from app.db.models import CameraRegistry, VehicleEvent, VehicleIdentity

# (cam_id, lat, lon): three real Gujarat coordinates with known rough
# distances, so tests run against real-world numbers rather than made-up ones.
CAM_A = ("cam_a", 23.0338, 72.5619)  # Ahmedabad - CG Road Jn
CAM_NEAR = ("cam_near", 23.0330, 72.5620)  # ~100 m from cam_a (same junction)
CAM_FAR = ("cam_far", 22.3072, 73.1812)  # Vadodara, ~103 km from cam_a
CAM_NOGPS = ("cam_nogps", None, None)

T0 = dt.datetime(2026, 9, 1, 10, 0, 0)


def _embed(seed: int) -> np.ndarray:
    """L2-normalized random vector of EMBEDDING_DIM. Same seed = identical
    embedding (cosine 1.0, the strongest possible appearance evidence); a
    different seed gives an uncorrelated vector (cosine ~0.15, far below the
    0.80 floor) — this keeps the tests focused on identity logic rather than
    re-wiring the color-histogram encoder."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(48).astype(np.float32)
    norm = np.linalg.norm(v)
    return v / norm


@pytest.fixture()
def resolver():
    return IdentityResolver()


@pytest.fixture()
def cameras(session):
    for cam_id, lat, lon in (CAM_A, CAM_NEAR, CAM_FAR, CAM_NOGPS):
        session.add(CameraRegistry(id=cam_id, latitude=lat, longitude=lon))
    session.commit()


def test_geo_infeasible_appearance_match_is_rejected(session, cameras, resolver):
    """(a) ~103 km apart in 60 s is ~6000 km/h — the gate must exclude the
    candidate outright, and the sighting becomes a NEW identity."""
    e = _embed(1)
    first, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])
    assert first.plate is None

    t1 = T0 + dt.timedelta(seconds=60)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_FAR[0])

    assert second.id != first.id
    assert link.method == "new_identity"
    assert session.query(VehicleIdentity).count() == 2


def test_geo_feasible_appearance_match_links(session, cameras, resolver):
    """(b) Same junction ~100 m apart: identical appearance, plausible
    timing -> same identity continued by appearance."""
    e = _embed(2)
    first, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])

    t1 = T0 + dt.timedelta(minutes=2)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_NEAR[0])

    assert second.id == first.id
    assert link.method == "appearance_match"
    assert link.score == pytest.approx(1.0, abs=1e-3)
    assert link.time_gap_s == pytest.approx(120.0, abs=0.1)


def test_geo_feasible_appearance_match_across_city_within_window(session, cameras, resolver):
    """(b, cross-city) ~103 km in 58 min is ~107 km/h — feasible, and still
    inside the 60-minute association window."""
    e = _embed(3)
    first, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])

    t1 = T0 + dt.timedelta(minutes=58)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_FAR[0])

    assert second.id == first.id
    assert link.method == "appearance_match"


def test_appearance_match_past_association_window_is_rejected(session, cameras, resolver):
    """The 60-minute window is the outer bound on candidate lookup — even a
    fully feasible match outside it must not link (identity would otherwise
    accumulate indefinitely)."""
    e = _embed(4)
    first, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])

    t1 = T0 + ASSOCIATION_WINDOW + dt.timedelta(seconds=1)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_NEAR[0])

    assert second.id != first.id
    assert link.method == "new_identity"


def test_dissimilar_appearance_not_linked_even_when_feasible(session, cameras, resolver):
    """Below the 0.80 similarity floor, a feasible candidate is still not
    linked — appearance must actually match, not just be physically possible."""
    first, _ = resolver.resolve(session, None, None, _embed(5), T0, CAM_A[0])

    t1 = T0 + dt.timedelta(minutes=2)
    second, link = resolver.resolve(session, None, None, _embed(6), t1, CAM_NEAR[0])

    assert second.id != first.id
    assert link.method == "new_identity"


def test_missing_gps_does_not_block_appearance_match(session, cameras, resolver):
    """Incomplete registry must not silently over-reject: if the new
    sighting's camera has no GPS, feasibility can't be assessed, so the gate
    passes rather than guessing (identity.py docstring, honest stance)."""
    e = _embed(7)
    first, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])

    t1 = T0 + dt.timedelta(minutes=2)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_NOGPS[0])

    assert second.id == first.id
    assert link.method == "appearance_match"


def test_direct_plate_reread_continues_identity_without_geo_gate(session, cameras, resolver):
    """(c) The gate is appearance-only. A plate re-read 103 km away in 5 s
    (physically impossible, ~70,000 km/h) STILL continues the identity —
    plate reads are strong ground truth and must never be gated."""
    e = _embed(8)
    first, _ = resolver.resolve(session, "GJ01AB1234", 0.90, e, T0, CAM_A[0])

    t1 = T0 + dt.timedelta(seconds=5)
    second, link = resolver.resolve(session, "GJ01AB1234", 0.85, e, t1, CAM_FAR[0])

    assert second.id == first.id
    assert link.method == "plate_continuation"
    assert second.last_camera_id == CAM_FAR[0]
    # plate_confidence only ratchets up, never down (0.90 from the first read)
    assert second.plate_confidence == pytest.approx(0.90)
    assert session.query(VehicleIdentity).filter_by(plate="GJ01AB1234").count() == 1


def test_plate_upgrade_retro_links_anonymous_identity(session, cameras, resolver):
    """(d) Anonymous identity seen at cam_a; later a CAMERA reads its plate.
    The upgrade must land on the SAME identity row (id preserved), so the
    earlier anonymous VehicleEvent stays retro-linked to the plate."""
    e = _embed(9)
    anon, _ = resolver.resolve(session, None, None, e, T0, CAM_A[0])
    assert anon.plate is None

    event = VehicleEvent(
        identity_id=anon.id, camera_id=CAM_A[0], pts_ms=0.0, observed_at=T0
    )
    session.add(event)
    session.commit()
    event_id = event.id

    t1 = T0 + dt.timedelta(minutes=58)  # feasible: ~103 km in 58 min
    upgraded, link = resolver.resolve(session, "GJ01AB1234", 0.93, e, t1, CAM_FAR[0])

    assert upgraded.id == anon.id
    assert upgraded.plate == "GJ01AB1234"
    assert link.method == "plate_upgrade"
    assert link.score == pytest.approx(1.0, abs=1e-3)

    again = session.get(VehicleEvent, event_id)
    assert again.identity_id == anon.id


def test_plated_identity_can_be_continued_by_anonymous_sighting(session, cameras, resolver):
    """A plated vehicle whose NEXT camera can't read its plate must still
    attach to the known identity (not spawn a new anonymous one)."""
    e = _embed(10)
    plated, _ = resolver.resolve(session, "GJ01AB1234", 0.90, e, T0, CAM_A[0])

    t1 = T0 + dt.timedelta(minutes=2)
    second, link = resolver.resolve(session, None, None, e, t1, CAM_NEAR[0])

    assert second.id == plated.id
    assert second.plate == "GJ01AB1234"
    assert link.method == "appearance_match"