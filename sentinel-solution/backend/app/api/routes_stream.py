"""Authenticated HLS proxy for the frontend live-view feature.

Why this exists: per HACKATHON_DETAILS.md §13a, HLS is served from the CDN
host behind the sandbox access password (a session cookie), not a bearer
token a browser can attach itself. The backend already holds that
authenticated session (catalogue.py, used to poll cameras.json). Rather than
handing the sandbox password to every browser tab, the frontend requests
`/live/{camera_id}/index.m3u8` from US, and we fetch+relay it through the
session we already have — rewriting any relative segment URLs in the
playlist to route back through this same proxy.

This is exactly the "WebRTC/HLS relay" piece the hackathon's own suggested
Model 2 stack lists — not a new middleware layer, just what's needed to make
a password-gated feed playable in a browser at all.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

from fastapi import APIRouter, Depends, HTTPException, Response

from ..catalogue import catalogue
from .auth import Principal, require_role

logger = logging.getLogger("sentinel.stream")

router = APIRouter(prefix="/live", tags=["live"])


@router.get("/{camera_id}/index.m3u8")
def hls_playlist(camera_id: str, _principal: Principal = Depends(require_role("viewer"))):
    cam = catalogue.get(camera_id)
    if cam is None:
        raise HTTPException(404, "unknown camera id — check /cameras")

    try:
        resp = catalogue.authenticated_get(cam.hls_url)
    except Exception as exc:  # noqa: BLE001 — surface as a clean 502, not a stack trace
        logger.warning("HLS playlist fetch failed for %s: %s", camera_id, exc)
        raise HTTPException(502, f"upstream HLS fetch failed: {exc}") from None

    rewritten_lines = []
    for line in resp.text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "://" not in stripped:
            # Relative segment/sub-playlist reference — route it back through
            # our proxy, resolved against the original playlist URL so
            # nested relative paths (subdirectories) still work.
            absolute = urljoin(cam.hls_url, stripped)
            rewritten_lines.append(f"/live/{camera_id}/seg?u={absolute}")
        else:
            rewritten_lines.append(line)

    return Response(
        content="\n".join(rewritten_lines),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{camera_id}/seg")
def hls_segment(camera_id: str, u: str, _principal: Principal = Depends(require_role("viewer"))):
    """Proxies one HLS segment (or nested sub-playlist) — `u` is the absolute
    upstream URL captured by hls_playlist() above, kept on our own /live
    path so the browser never needs the CDN session directly.

    `u` is client-supplied (it round-trips through the browser's playlist
    fetch), so it MUST be restricted to the camera's own HLS host before
    we fetch it with our authenticated session — otherwise this endpoint is
    an open SSRF proxy that fetches ANY url using the sandbox credentials.
    """
    cam = catalogue.get(camera_id)
    if cam is None:
        raise HTTPException(404, "unknown camera id")

    expected_host = urlparse(cam.hls_url).netloc
    if urlparse(u).netloc != expected_host:
        raise HTTPException(400, "segment url host does not match this camera's HLS host")

    try:
        resp = catalogue.authenticated_get(u)
    except Exception as exc:  # noqa: BLE001
        logger.warning("HLS segment fetch failed for %s (%s): %s", camera_id, u, exc)
        raise HTTPException(502, f"upstream segment fetch failed: {exc}") from None

    content_type = resp.headers.get("Content-Type", "video/mp2t")
    return Response(content=resp.content, media_type=content_type)
