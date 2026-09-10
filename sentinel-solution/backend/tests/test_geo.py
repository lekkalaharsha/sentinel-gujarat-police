"""Regression tests for analytics/geo.py (SWE-4).

Guards the three documented failure modes, all caught previously by manual
testing only:
- haversine sanity against known real-world distances;
- `rank_candidate_cameras` must not crash or emit nonsense "required speed"
  when elapsed time is non-positive (the hardcoded-future-date bug) or when
  either side lacks GPS;
- `build_inferred_segments` handles plausible, implausible, non-positive-gap
  and missing-GPS pairs without lying about feasibility.
"""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from app.analytics.geo import (
    MAX_PLAUSIBLE_KMH,
    RoutePoint,
    build_inferred_segments,
    haversine_km,
    rank_candidate_cameras,
)


def _cam(cam_id: str, lat, lon):
    return SimpleNamespace(id=cam_id, location_name=cam_id, latitude=lat, longitude=lon)


# --- haversine_km -----------------------------------------------------------

def test_haversine_zero_at_same_point():
    assert haversine_km(23.0338, 72.5619, 23.0338, 72.5619) == 0.0


def test_haversine_degree_of_latitude_is_about_111km():
    d = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111.19, abs=0.5)


def test_haversine_ahmedabad_vadodara_within_expected_range():
    d = haversine_km(23.0338, 72.5619, 22.3072, 73.1812)
    assert 95.0 < d < 115.0


# --- rank_candidate_cameras -------------------------------------------------

def test_rank_candidate_cameras_non_positive_elapsed_returns_empty():
    """The regression: a future/stale observed_at produced a negative elapsed
    time and nonsense negative 'required speed'. Guarded to return []."""
    last = _cam("cam_a", 23.0338, 72.5619)
    others = [_cam("cam_far", 22.3072, 73.1812)]
    future = dt.datetime.utcnow() + dt.timedelta(hours=1)
    assert rank_candidate_cameras(last, future, others) == []


def test_rank_candidate_cameras_missing_geo_returns_empty():
    """No GPS on either side -> nothing to reason about, honestly empty,
    never a guess."""
    assert rank_candidate_cameras(None, dt.datetime.utcnow(), []) == []
    nogps = _cam("cam_nogps", None, None)
    assert rank_candidate_cameras(nogps, dt.datetime.utcnow(), [_cam("cam_b", 1.0, 1.0)]) == []


def test_rank_candidate_cameras_feasible_vs_eliminated():
    last = _cam("cam_a", 23.0338, 72.5619)
    near = _cam("cam_near", 23.0330, 72.5620)  # ~100 m away
    far = _cam("cam_far", 28.6139, 77.2090)  # Delhi, ~780 km away
    observed_at = dt.datetime.utcnow() - dt.timedelta(hours=1)

    ranked = rank_candidate_cameras(last, observed_at, [near, far])
    assert len(ranked) == 2

    by_id = {r["camera_id"]: r for r in ranked}
    assert by_id["cam_near"]["status"] == "FEASIBLE"
    assert by_id["cam_far"]["status"] == "ELIMINATED"
    assert by_id["cam_far"]["required_min_speed_kmh"] > MAX_PLAUSIBLE_KMH
    assert by_id["cam_near"]["required_min_speed_kmh"] <= MAX_PLAUSIBLE_KMH
    # eliminated last: sorted ascending by required speed
    assert [r["camera_id"] for r in ranked] == ["cam_near", "cam_far"]


def test_rank_candidate_cameras_excludes_self():
    last = _cam("cam_a", 23.0338, 72.5619)
    observed_at = dt.datetime.utcnow() - dt.timedelta(hours=1)
    assert rank_candidate_cameras(last, observed_at, [last]) == []


# --- build_inferred_segments ------------------------------------------------

def test_build_inferred_segments_same_camera_produces_none():
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 0, 0)),
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 5, 0)),
    ]
    assert build_inferred_segments(pts) == []


def test_build_inferred_segments_plausible_direct_drive():
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 0, 0)),
        RoutePoint("cam_near", 23.0330, 72.5620, dt.datetime(2026, 9, 1, 10, 12, 0)),
    ]
    seg = build_inferred_segments(pts)[0]
    assert seg["event_type"] == "INFERRED"
    assert seg["from_camera"] == "cam_a"
    assert seg["to_camera"] == "cam_near"
    assert seg["plausible_direct_drive"] is True
    assert seg["implied_min_speed_kmh"] is not None
    assert seg["implied_min_speed_kmh"] <= MAX_PLAUSIBLE_KMH


def test_build_inferred_segments_implausible_direct_drive():
    """~103 km in 30 min is ~206 km/h straight-line — a confident 'NOT a
    simple direct drive' signal (unmonitored detour, or different vehicle)."""
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 0, 0)),
        RoutePoint("cam_far", 22.3072, 73.1812, dt.datetime(2026, 9, 1, 10, 30, 0)),
    ]
    seg = build_inferred_segments(pts)[0]
    assert seg["plausible_direct_drive"] is False
    assert seg["implied_min_speed_kmh"] > MAX_PLAUSIBLE_KMH
    assert "exceeding" in seg["basis"]


def test_build_inferred_segments_non_positive_gap_is_unassessable():
    """Clock skew between cameras: negative gap means feasibility can't be
    claimed either way — must stay None, not a bogus number."""
    t = dt.datetime(2026, 9, 1, 10, 0, 0)
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, t),
        RoutePoint("cam_near", 23.0330, 72.5620, t - dt.timedelta(seconds=5)),
    ]
    seg = build_inferred_segments(pts)[0]
    assert seg["implied_min_speed_kmh"] is None
    assert seg["plausible_direct_drive"] is None
    assert "non-positive" in seg["basis"]


def test_build_inferred_segments_missing_gps_is_unassessable():
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 0, 0)),
        RoutePoint("cam_nogps", None, None, dt.datetime(2026, 9, 1, 10, 10, 0)),
    ]
    seg = build_inferred_segments(pts)[0]
    assert seg["distance_km"] is None
    assert seg["implied_min_speed_kmh"] is None
    assert seg["plausible_direct_drive"] is None
    assert "no GIS coordinates" in seg["basis"]


def test_build_inferred_segments_three_points_skips_same_camera_pair():
    pts = [
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 0, 0)),
        RoutePoint("cam_a", 23.0338, 72.5619, dt.datetime(2026, 9, 1, 10, 5, 0)),
        RoutePoint("cam_far", 22.3072, 73.1812, dt.datetime(2026, 9, 1, 10, 35, 0)),
    ]
    segs = build_inferred_segments(pts)
    assert len(segs) == 1  # only the cam_a -> cam_far hop is a real jump
    assert segs[0]["from_camera"] == "cam_a"
    assert segs[0]["to_camera"] == "cam_far"