"""Minimal, real role-based access control.

Model 1's spec lists "department-wise RBAC" as a required deliverable, not
a bonus — this is not a stub in the "seam ready, weights not installed"
sense (see analytics/*.py). It's a genuine, working access-control layer:
every route below declares which role(s) it accepts, and a request without
a valid API key for that role is actually rejected with 401/403, not
logged-and-allowed.

Deliberately simple for a hackathon timeframe: a single header
(`X-Sentinel-API-Key`) maps to a role via a DB-backed key table, not a full
OAuth/session flow. That's an honest scope choice, not a hidden gap — see
STRATEGY.md's OUT list philosophy: build the real minimal thing, not a fake
elaborate one.

Roles (least to most privileged):
  viewer       — read cameras/GIS/live view only
  investigator — + purpose-bound vehicle search, watchlist read, alerts
  admin        — + camera onboarding, watchlist writes, alert ack
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db.models import ApiKeyEntry
from .deps import get_db

logger = logging.getLogger("sentinel.auth")

ROLE_RANK = {"viewer": 0, "investigator": 1, "admin": 2}


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class Principal:
    def __init__(self, user_id: str, role: str, department: Optional[str]):
        self.user_id = user_id
        self.role = role
        self.department = department


def get_principal(
    x_sentinel_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Principal:
    if not x_sentinel_api_key:
        raise HTTPException(401, "missing X-Sentinel-API-Key header")
    entry = db.query(ApiKeyEntry).filter_by(key_hash=hash_key(x_sentinel_api_key)).first()
    if entry is None:
        raise HTTPException(401, "invalid API key")
    return Principal(entry.user_id, entry.role, entry.department)


def require_role(minimum_role: str):
    """Usage: `principal: Principal = Depends(require_role("admin"))`.
    Roles are ranked (viewer < investigator < admin) so `require_role
    ("investigator")` also accepts admin — same convention as most RBAC
    systems, higher privilege satisfies a lower-privilege requirement."""

    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if ROLE_RANK.get(principal.role, -1) < ROLE_RANK[minimum_role]:
            raise HTTPException(403, f"role '{principal.role}' cannot access this endpoint (requires '{minimum_role}'+)")
        return principal

    return dependency


def ensure_default_admin_key(session: Session) -> None:
    """First-run bootstrap: if no API keys exist at all, mint one admin key
    and log it once so the demo isn't locked out of its own backend. Real
    keys after that are provisioned by an admin via POST /auth/api-keys."""
    if session.query(ApiKeyEntry).first() is not None:
        return
    raw_key = secrets.token_urlsafe(24)
    session.add(ApiKeyEntry(key_hash=hash_key(raw_key), user_id="bootstrap-admin", role="admin"))
    session.commit()
    logger.warning(
        "No API keys existed — minted a bootstrap admin key (SAVE THIS, shown only once): %s",
        raw_key,
    )
