"""Geo-temporal route reconstruction — the honest 'inferred journey' layer.

Between two CONFIRMED (OBSERVED) sightings of the same vehicle at different
cameras, there is usually road the vehicle travelled with NO camera evidence.
This module represents that gap explicitly as an INFERRED segment, rather
than pretending the vehicle was "tracked" continuously through it. That
distinction is the point: for a police tool, inferred movement must never be
presented as observed fact (see STRATEGY.md / HLD §5).

Deliberately dependency-free and honest about its limits:
- Distance is STRAIGHT-LINE (haversine) between camera GPS, a LOWER BOUND on
  the real road distance. So the implied straight-line speed is a lower bound
  on the speed actually required. We use that asymmetry correctly: a *high*
  implied straight-line speed is strong evidence the gap is NOT a simple
  direct drive (an unmonitored detour, or two different vehicles) — whereas a
  low implied speed only means direct travel is *feasible*, not confirmed.
- No road-network / OSM routing here (that needs external data we don't have
  for Gujarat's minor roads — documented as roadmap). This is the honest,
  buildable approximation, labelled as such.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass
from typing import List, Optional

EARTH_RADIUS_KM = 6371.0

# Generous ceiling for a plausible ground vehicle. Because straight-line
# distance UNDER-estimates road distance, exceeding this on the straight-line
# figure alone is a confident "this isn't a direct drive" signal.
MAX_PLAUSIBLE_KMH = 120.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


@dataclass
class RoutePoint:
    camera_id: str
    latitude: Optional[float]
    longitude: Optional[float]
    observed_at: dt.datetime


@dataclass
class InferredSegment:
    event_type: str  # always "INFERRED"
    from_camera: str
    to_camera: str
    time_gap_s: float
    distance_km: Optional[float]          # None if either camera lacks GPS
    implied_min_speed_kmh: Optional[float]  # straight-line lower bound
    plausible_direct_drive: Optional[bool]  # None if distance/time unknown
    basis: str  # human-readable explanation of the inference


def build_inferred_segments(points: List[RoutePoint]) -> List[dict]:
    """Given time-ordered OBSERVED points, emit an INFERRED segment for each
    consecutive pair at DIFFERENT cameras. Same-camera consecutive points
    (dwelling in one view) produce no segment."""
    segments: List[dict] = []
    for a, b in zip(points, points[1:]):
        if a.camera_id == b.camera_id:
            continue
        time_gap_s = (b.observed_at - a.observed_at).total_seconds()

        if None in (a.latitude, a.longitude, b.latitude, b.longitude):
            seg = InferredSegment(
                event_type="INFERRED",
                from_camera=a.camera_id, to_camera=b.camera_id,
                time_gap_s=round(time_gap_s, 1),
                distance_km=None, implied_min_speed_kmh=None,
                plausible_direct_drive=None,
                basis="inferred from observation order only - one or both cameras "
                      "have no GIS coordinates, so distance/speed feasibility can't be assessed",
            )
            segments.append(asdict(seg))
            continue

        distance_km = haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
        if time_gap_s > 0:
            implied_kmh = distance_km / (time_gap_s / 3600.0)
            plausible = implied_kmh <= MAX_PLAUSIBLE_KMH
            if plausible:
                basis = (f"straight-line {distance_km:.2f} km in {time_gap_s:.0f}s => "
                         f">={implied_kmh:.0f} km/h required; within plausible range - "
                         f"direct travel is FEASIBLE (not confirmed; no camera evidence on this segment)")
            else:
                basis = (f"straight-line {distance_km:.2f} km in {time_gap_s:.0f}s => "
                         f">={implied_kmh:.0f} km/h required, exceeding {MAX_PLAUSIBLE_KMH:.0f} km/h even "
                         f"on a lower-bound straight line - NOT a simple direct drive (unmonitored detour, "
                         f"or possibly a different vehicle)")
        else:
            implied_kmh = None
            plausible = None
            basis = (f"straight-line {distance_km:.2f} km but non-positive time gap "
                     f"({time_gap_s:.0f}s) - camera clocks may be unsynchronised; feasibility unassessable")

        segments.append(asdict(InferredSegment(
            event_type="INFERRED",
            from_camera=a.camera_id, to_camera=b.camera_id,
            time_gap_s=round(time_gap_s, 1),
            distance_km=round(distance_km, 2),
            implied_min_speed_kmh=round(implied_kmh, 1) if implied_kmh is not None else None,
            plausible_direct_drive=plausible,
            basis=basis,
        )))
    return segments
