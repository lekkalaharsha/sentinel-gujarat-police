"""Model 2's "unified viewer connecting >=2 different systems" deliverable —
System B: Caltrans District 3's real, public, unauthenticated CCTV API
(https://cwwp2.dot.ca.gov/data/d3/cctv/cctvStatusD03.json).

Why this and not a second Gujarat departmental VMS: none is available to
integrate against (see docs/models/model-2-unified-viewing/IMPLEMENTATION_PLAN.md
— "don't simulate a fake second system to check this box"). Caltrans is a
real, independently-operated government traffic-camera system, reachable
over plain HTTPS with no API key, that publishes live-refreshed camera
imagery. It proves genuine direct API integration with a second system,
honestly: no ANPR/analytics runs on these cameras (out of scope, and
Caltrans imagery isn't in-scope Gujarat evidence), and the frontend must
never render these tiles as if they were continuous live video — they are
periodically-refreshed still images, labelled as such everywhere.

Registry-only: these cameras are written directly into CameraRegistry, not
into catalogue.py's CatalogueClient, so StreamManager/the ANPR pipeline
never sees them and never attempts to open them as RTSP streams.
"""
from __future__ import annotations

import datetime as dt
import logging

import requests
from sqlalchemy.orm import Session

from . import config
from .db.models import CameraRegistry

logger = logging.getLogger("sentinel.external_camera_source")

SOURCE_SYSTEM = "caltrans_d3_public_api"
SOURCE_LABEL = "Caltrans District 3 (public traffic-camera API, cwwp2.dot.ca.gov)"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def fetch_raw(url: str = config.EXTERNAL_CAMERA_SOURCE_URL, timeout: float = 30.0) -> dict:
    # The real endpoint's full per-district payload is ~850KB (hundreds of
    # cameras, we only keep the first EXTERNAL_CAMERA_SOURCE_MAX_CAMERAS
    # after fetching) and observed taking 13+ seconds end to end in real
    # testing — a 10s timeout genuinely failed against the live API.
    """Real network call, split out so parse() can be unit-tested against a
    fixture without hitting the internet."""
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def parse(payload: dict, max_cameras: int) -> list[dict]:
    """Pure function: Caltrans JSON -> normalized camera dicts. Only
    `inService` cameras with a usable snapshot image URL are kept — an
    offline entry with no image would show a permanently broken tile,
    which is worse than just not onboarding it. Namespaced ids
    (`ext-caltrans-<index>`) so they can never collide with a Gujarat
    sandbox camera id."""
    entries = payload.get("data", []) if isinstance(payload, dict) else []
    out: list[dict] = []
    for entry in entries:
        cctv = entry.get("cctv") or {}
        location = cctv.get("location") or {}
        image = (cctv.get("imageData") or {}).get("static") or {}
        in_service = str(cctv.get("inService", "")).lower() == "true"
        snapshot_url = image.get("currentImageURL")
        if not in_service or not snapshot_url:
            continue
        index = cctv.get("index")
        if index is None:
            continue
        try:
            lat = float(location.get("latitude"))
            lon = float(location.get("longitude"))
        except (TypeError, ValueError):
            lat = lon = None
        name = location.get("locationName") or f"Caltrans D3 camera {index}"
        out.append({
            "id": f"ext-caltrans-{index}",
            "location_name": f"{name} ({location.get('nearbyPlace') or 'CA'})",
            "latitude": lat,
            "longitude": lon,
            "snapshot_image_url": snapshot_url,
            "in_service": in_service,
        })
        if len(out) >= max_cameras:
            break
    return out


def sync_into_registry(
    session: Session,
    max_cameras: int = config.EXTERNAL_CAMERA_SOURCE_MAX_CAMERAS,
) -> int:
    """Upsert into CameraRegistry, same idempotent-upsert shape as
    routes_cameras.py's onboard_camera. Never touches a row belonging to a
    different source_system (defensive — should be impossible given the
    `ext-caltrans-` id prefix, but this keeps a future bug from letting an
    external sync silently overwrite a real Gujarat camera's metadata)."""
    cameras = parse(fetch_raw(), max_cameras)
    now = dt.datetime.utcnow()
    for cam in cameras:
        existing = session.get(CameraRegistry, cam["id"])
        if existing is None:
            existing = CameraRegistry(id=cam["id"], source_system=SOURCE_SYSTEM)
            session.add(existing)
        elif existing.source_system != SOURCE_SYSTEM:
            logger.warning(
                "skipping external sync for %s — id collides with a non-external registry row",
                cam["id"],
            )
            continue
        existing.department = f"External — {SOURCE_LABEL}"
        existing.location_name = cam["location_name"]
        existing.latitude = cam["latitude"]
        existing.longitude = cam["longitude"]
        existing.camera_type = "highway-cctv-external"
        existing.source_system = SOURCE_SYSTEM
        existing.snapshot_image_url = cam["snapshot_image_url"]
        existing.is_healthy = cam["in_service"]
        existing.last_seen_live_at = now
    session.commit()
    return len(cameras)
