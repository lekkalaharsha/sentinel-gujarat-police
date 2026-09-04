from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..catalogue import catalogue
from ..db.models import CameraRegistry
from .auth import Principal, require_role
from .deps import get_db

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Camera health is considered stale (and reported unhealthy) if no frame has
# arrived in this long, even if the worker's socket still looks "connected"
# — matches the sandbox guide's own note that feeds can stall mid-stream.
HEALTH_STALE_S = 90.0


def _merged_camera_view(session: Session, cam_id: str, live_info) -> dict:
    """Model 1's registry is metadata-first (see HACKATHON_DETAILS.md §7):
    a camera can be "registered" (in CameraRegistry, with department/GIS
    metadata) independently of whether it's currently live in the
    catalogue. Earlier versions of this endpoint only read the live
    catalogue and silently dropped department/lat/lon/health — merging both
    sources here is the actual fix for that."""
    registry = session.get(CameraRegistry, cam_id)
    return {
        "id": cam_id,
        "location": (live_info.location if live_info else None) or (registry.location_name if registry else None),
        "codec": live_info.codec if live_info else None,
        "live": bool(live_info),
        "rtsp_url": live_info.rtsp_url if live_info else None,
        "whep_url": live_info.whep_url if live_info else None,
        "hls_url": live_info.hls_url if live_info else None,
        "department": registry.department if registry else None,
        "vendor": registry.vendor if registry else None,
        "latitude": registry.latitude if registry else None,
        "longitude": registry.longitude if registry else None,
        "is_healthy": registry.is_healthy if registry else None,
        "last_seen_live_at": registry.last_seen_live_at.isoformat() if registry and registry.last_seen_live_at else None,
        "onboarded": registry is not None,
    }


@router.get("")
def list_cameras(db: Session = Depends(get_db), _principal: Principal = Depends(require_role("viewer"))):
    """Model 1 view: union of the live catalogue AND the onboarded registry
    — a camera that's registered but currently offline (a real gap-analysis
    case) still shows up, just with live=false."""
    live = catalogue.cameras
    registered = db.query(CameraRegistry).all()
    all_ids = set(live.keys()) | {r.id for r in registered}
    return [_merged_camera_view(db, cam_id, live.get(cam_id)) for cam_id in sorted(all_ids)]


@router.get("/gap-analysis")
def gap_analysis(db: Session = Depends(get_db), _principal: Principal = Depends(require_role("investigator"))):
    """Model 1 explicitly requires a 'gap-analysis report' deliverable:
    which cameras are known but not onboarded with metadata, which are
    onboarded but not currently live, and department coverage — the
    concrete gaps a real rollout would need to close next."""
    live = catalogue.cameras
    registered = {r.id: r for r in db.query(CameraRegistry).all()}

    live_not_onboarded = sorted(set(live) - set(registered))
    onboarded_not_live = sorted(set(registered) - set(live))
    missing_department = sorted(cid for cid, r in registered.items() if not r.department)
    missing_gis = sorted(cid for cid, r in registered.items() if r.latitude is None or r.longitude is None)
    unhealthy = sorted(cid for cid, r in registered.items() if r.is_healthy is False)

    by_department: dict[str, int] = {}
    for r in registered.values():
        key = r.department or "unassigned"
        by_department[key] = by_department.get(key, 0) + 1

    return {
        "catalogue_size": len(live),
        "registered_size": len(registered),
        "live_not_onboarded": live_not_onboarded,
        "onboarded_not_live": onboarded_not_live,
        "missing_department": missing_department,
        "missing_gis_coordinates": missing_gis,
        "unhealthy": unhealthy,
        "cameras_by_department": by_department,
    }


class CameraOnboard(BaseModel):
    id: str
    department: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    vendor: str | None = None


@router.post("")
def onboard_camera(
    body: CameraOnboard,
    db: Session = Depends(get_db),
    _admin: Principal = Depends(require_role("admin")),
):
    """Model 1's 'API-based onboarding' / 'manual onboarding' deliverable.
    Upsert: onboarding an already-known camera updates its metadata rather
    than erroring, since re-running a bulk import with corrected data is a
    normal workflow, not an edge case."""
    existing = db.get(CameraRegistry, body.id)
    if existing is None:
        existing = CameraRegistry(id=body.id)
        db.add(existing)
    existing.department = body.department
    existing.location_name = body.location_name
    existing.latitude = body.latitude
    existing.longitude = body.longitude
    existing.vendor = body.vendor
    db.commit()
    return {"status": "onboarded", "id": body.id}


@router.post("/bulk")
def onboard_cameras_bulk(
    bodies: list[CameraOnboard],
    db: Session = Depends(get_db),
    _admin: Principal = Depends(require_role("admin")),
):
    """Bulk-import deliverable — same upsert semantics as onboard_camera,
    looped in one transaction so a 50-camera CSV-derived import is one call."""
    ids = []
    for body in bodies:
        existing = db.get(CameraRegistry, body.id)
        if existing is None:
            existing = CameraRegistry(id=body.id)
            db.add(existing)
        existing.department = body.department
        existing.location_name = body.location_name
        existing.latitude = body.latitude
        existing.longitude = body.longitude
        existing.vendor = body.vendor
        ids.append(body.id)
    db.commit()
    return {"status": "onboarded", "count": len(ids), "ids": ids}


@router.get("/{camera_id}")
def get_camera(camera_id: str, db: Session = Depends(get_db), _principal: Principal = Depends(require_role("viewer"))):
    live_info = catalogue.get(camera_id)
    registry = db.get(CameraRegistry, camera_id)
    if live_info is None and registry is None:
        return {"error": "not found"}
    return _merged_camera_view(db, camera_id, live_info)
