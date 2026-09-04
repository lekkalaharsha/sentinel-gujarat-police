"""Implements the evaluation's core ask: given a plate, return the complete
timestamped, location-wise movement history across the camera network.

Every lookup is purpose-bound and logged (DPDP-oriented governance): the
caller must state who they are and why they're querying, not just what.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..analytics.anpr import normalize_plate
from ..analytics.geo import RoutePoint, build_inferred_segments
from ..db.models import AuditLog, CameraRegistry, VehicleEvent, VehicleIdentity
from .auth import Principal, require_role
from .deps import get_db

router = APIRouter(prefix="/vehicle", tags=["vehicle"])

# Temporal consistency decays from 1.0 (instant) to ~0 at this many seconds
# since the identity's previous sighting — informs the fused score below but
# is a hand-picked heuristic, not a learned weighting.
_TEMPORAL_DECAY_S = 15 * 60


def _explain_link(e: VehicleEvent) -> dict:
    """"Why was this vehicle linked?" — surfaces the raw signals behind
    identity resolution (see analytics/identity.py) plus a simple weighted
    fused score. This is a transparency aid for investigators, not a
    calibrated probability: weights are fixed heuristics (plate confidence
    is the strongest signal per STRATEGY.md's plate-first principle)."""
    plate_confidence = e.plate_confidence or 0.0
    reid_similarity = e.link_score or 0.0
    if e.link_time_gap_s is None:
        temporal_consistency = None
    else:
        temporal_consistency = max(0.0, 1.0 - (e.link_time_gap_s / _TEMPORAL_DECAY_S))

    if e.link_method in ("new_identity",):
        fused_score = plate_confidence if e.plate_confidence else None
    elif e.link_method == "plate_continuation":
        fused_score = plate_confidence
    else:  # plate_upgrade, appearance_match — appearance carried the link
        fused_score = round(
            0.5 * plate_confidence + 0.35 * reid_similarity + 0.15 * (temporal_consistency or 0.0), 3
        )

    return {
        "method": e.link_method,
        "reid_similarity": e.link_score,
        "time_since_previous_sighting_s": e.link_time_gap_s,
        "temporal_consistency": temporal_consistency,
        "fused_score": fused_score,
    }


@router.get("/{plate}/history")
def vehicle_history(
    plate: str,
    purpose: str,
    case_id: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("investigator")),
):
    """Returns the FULL movement history for this plate's identity —
    including sightings recorded before ANPR ever read the plate. If the
    vehicle was seen anonymously (unreadable plate) at earlier cameras and
    later matched by appearance to this same identity, those anonymous
    sightings are part of the timeline too (see identity.py). Querying by
    VehicleEvent.plate alone would miss them, since those historical rows
    correctly kept plate=NULL for what was actually known at the time.

    `user_id` on the audit log is the AUTHENTICATED principal from the API
    key, not a client-supplied string — a self-reported user_id would make
    the purpose-bound audit trail decorative rather than actually
    accountable (see api/auth.py's RBAC).
    """
    plate = normalize_plate(plate)
    db.add(AuditLog(user_id=principal.user_id, purpose=purpose, case_id=case_id, query=plate))
    db.commit()

    identity = db.query(VehicleIdentity).filter(VehicleIdentity.plate == plate).first()
    if identity is None:
        return {"plate": plate, "sightings": [], "note": "no identity has been resolved to this plate yet"}

    events = (
        db.query(VehicleEvent)
        .filter(VehicleEvent.identity_id == identity.id)
        .order_by(VehicleEvent.observed_at.asc())
        .all()
    )
    out = []
    route_points = []
    for e in events:
        cam = db.get(CameraRegistry, e.camera_id)
        out.append(
            {
                # Geo-temporal event typing: a sighting is CONFIRMED camera
                # evidence. The INFERRED gaps between sightings live in
                # `route_segments` below — kept as a separate, clearly-labelled
                # list so nothing reads an inference as an observation.
                "event_type": "OBSERVED",
                "camera_id": e.camera_id,
                "location": cam.location_name if cam else None,
                "latitude": cam.latitude if cam else None,
                "longitude": cam.longitude if cam else None,
                "pts_ms": e.pts_ms,
                "observed_at": e.observed_at.isoformat(),
                "confidence": e.confidence,
                "plate_read_at_this_camera": e.plate is not None,
                "plate_confidence": e.plate_confidence,
                "vehicle_type": e.vehicle_type,
                "color": e.color,
                "color_confidence": e.color_confidence,
                "dimensions_px": {"width": e.width_px, "height": e.height_px, "aspect_ratio": e.aspect_ratio},
                "make_model": e.make_model,
                # Image-plane motion metrics (NOT calibrated km/h — see
                # models.py). Useful for dwell/wrong-way/stopped filters.
                "motion": {
                    "dwell_time_s": e.dwell_time_s,
                    "speed_px_per_s": e.speed_px_per_s,
                    "direction_deg": e.direction_deg,
                },
                "link": _explain_link(e),
            }
        )
        route_points.append(
            RoutePoint(
                camera_id=e.camera_id,
                latitude=cam.latitude if cam else None,
                longitude=cam.longitude if cam else None,
                observed_at=e.observed_at,
            )
        )

    # Route reconstruction: OBSERVED sightings interleaved with INFERRED
    # segments for the camera-less gaps between them (geo-temporal layer —
    # see analytics/geo.py). Straight-line/lower-bound; honestly labelled.
    route_segments = build_inferred_segments(route_points)

    return {
        "plate": plate,
        "identity_id": identity.id,
        "identity_first_seen": identity.first_seen_at.isoformat(),
        "sightings": out,
        "route_segments": route_segments,
        "route_legend": {
            "OBSERVED": "confirmed CCTV evidence at a camera",
            "INFERRED": "camera-less gap between two confirmed sightings; feasibility "
                        "estimated from straight-line distance + time, never observed",
        },
    }


@router.get("/search-by-attributes")
def search_by_attributes(
    purpose: str,
    vehicle_type: str | None = None,
    color: str | None = None,
    partial_plate: str | None = None,
    case_id: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("investigator")),
):
    """Fallback for when ANPR can't produce a confident plate read on any
    frame: search by colour/type/partial-plate instead — what an
    investigator actually has when a plate is unreadable in the footage."""
    query_desc = f"type={vehicle_type} color={color} partial_plate={partial_plate}"
    db.add(AuditLog(user_id=principal.user_id, purpose=purpose, case_id=case_id, query=query_desc))
    db.commit()

    q = db.query(VehicleEvent)
    if vehicle_type:
        q = q.filter(VehicleEvent.vehicle_type == vehicle_type)
    if color:
        q = q.filter(VehicleEvent.color == color)
    if partial_plate:
        q = q.filter(VehicleEvent.plate.like(f"%{normalize_plate(partial_plate)}%"))
    events = q.order_by(VehicleEvent.observed_at.asc()).limit(200).all()

    out = []
    for e in events:
        cam = db.get(CameraRegistry, e.camera_id)
        out.append(
            {
                "camera_id": e.camera_id,
                "location": cam.location_name if cam else None,
                "observed_at": e.observed_at.isoformat(),
                "plate": e.plate,
                "plate_confidence": e.plate_confidence,
                "vehicle_type": e.vehicle_type,
                "color": e.color,
            }
        )
    return {"query": query_desc, "matches": out}
