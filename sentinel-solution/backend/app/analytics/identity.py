"""Cross-camera vehicle identity resolution.

This is the fix for "plate not readable -> tracking failed." Implements:

    Camera 1: plate ❌, white SUV, embedding e1
    Camera 2: plate ❌, white SUV, embedding e2  (~e1, similar) -> same identity
    Camera 3: plate ✅ GJ01AB1234, embedding e3  (~e1/e2, similar)
              -> identity upgraded to GJ01AB1234
              -> camera 1 and 2 sightings retroactively belong to this plate

We never claim a plate identity before it's actually observed — an
anonymous identity stays anonymous until ANPR succeeds on ANY of its
sightings; only then does the whole chain resolve to that plate. See
STRATEGY.md's "plate-first, appearance-second" principle: plate is the
strongest signal, appearance is what carries identity through the gaps.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Optional, Tuple

import numpy as np
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.models import VehicleIdentity
from .reid import cosine_similarity

# How long an identity stays eligible for cross-camera association after
# its last sighting. Wide enough to span a plausible multi-camera route
# within the sandbox's ~50-camera pilot, tight enough not to merge unrelated
# vehicles hours apart.
ASSOCIATION_WINDOW = dt.timedelta(minutes=15)
EMBEDDING_SIMILARITY_THRESHOLD = 0.80


@dataclasses.dataclass
class LinkInfo:
    """Why this sighting got attached to the identity it did — persisted
    onto the VehicleEvent so the "why was this vehicle linked?"
    explainability panel has real data instead of nothing. Captured here,
    at the moment of the match decision, because it can't be reconstructed
    later: VehicleIdentity only keeps its latest embedding, not history."""

    method: str  # "new_identity" | "plate_continuation" | "plate_upgrade" | "appearance_match"
    score: Optional[float] = None  # cosine similarity, only set for appearance_match
    time_gap_s: Optional[float] = None  # seconds since the identity's previous sighting


class IdentityResolver:
    def resolve(
        self,
        session: Session,
        plate: Optional[str],
        plate_confidence: Optional[float],
        embedding: np.ndarray,
        observed_at: dt.datetime,
    ) -> Tuple[VehicleIdentity, LinkInfo]:
        if plate:
            return self._resolve_with_plate(session, plate, plate_confidence, embedding, observed_at)
        return self._resolve_anonymous(session, embedding, observed_at)

    def _resolve_with_plate(
        self,
        session: Session,
        plate: str,
        plate_confidence: Optional[float],
        embedding: np.ndarray,
        observed_at: dt.datetime,
    ) -> Tuple[VehicleIdentity, LinkInfo]:
        # 1. Same plate already has an identity -> just continue it.
        existing = (
            session.query(VehicleIdentity)
            .filter(VehicleIdentity.plate == plate)
            .order_by(VehicleIdentity.last_seen_at.desc())
            .first()
        )
        if existing:
            gap_s = (observed_at - existing.last_seen_at).total_seconds()
            existing.last_seen_at = observed_at
            existing.set_embedding(embedding)
            if plate_confidence and (existing.plate_confidence or 0) < plate_confidence:
                existing.plate_confidence = plate_confidence
            session.commit()
            return existing, LinkInfo(method="plate_continuation", time_gap_s=gap_s)

        # 2. No identity has this plate yet — but an anonymous identity with
        #    a matching appearance might be THIS vehicle, seen earlier
        #    without a readable plate. Upgrade it instead of creating a
        #    disconnected new identity.
        candidate, score = self._best_anonymous_match(session, embedding, observed_at)
        if candidate is not None:
            gap_s = (observed_at - candidate.last_seen_at).total_seconds()
            candidate.plate = plate
            candidate.plate_confidence = plate_confidence
            candidate.last_seen_at = observed_at
            candidate.set_embedding(embedding)
            try:
                session.commit()
            except IntegrityError:
                # Another camera's worker thread committed an identity with
                # this exact plate between our SELECT above and this COMMIT
                # (each camera runs its own thread/session — see
                # streaming/manager.py — so this is a real, reachable race,
                # not theoretical). Discard our local upgrade and fall
                # through to the winner instead of creating a duplicate.
                session.rollback()
                return self._resolve_with_plate(session, plate, plate_confidence, embedding, observed_at)
            return candidate, LinkInfo(method="plate_upgrade", score=score, time_gap_s=gap_s)

        # 3. Genuinely new, plate known from the start.
        identity = VehicleIdentity(
            plate=plate, plate_confidence=plate_confidence,
            first_seen_at=observed_at, last_seen_at=observed_at,
        )
        identity.set_embedding(embedding)
        session.add(identity)
        try:
            session.commit()
        except IntegrityError:
            # Same race as above: another thread's identity for this plate
            # landed first. Re-resolve — this time the plate exists, so we
            # take the "continue existing" path (case 1) instead of a retry
            # loop, since the losing `identity` object above is never
            # persisted (rolled back) and safely discarded.
            session.rollback()
            return self._resolve_with_plate(session, plate, plate_confidence, embedding, observed_at)
        return identity, LinkInfo(method="new_identity")

    def _resolve_anonymous(
        self, session: Session, embedding: np.ndarray, observed_at: dt.datetime
    ) -> Tuple[VehicleIdentity, LinkInfo]:
        # Try to continue an existing identity (anonymous OR already-plated —
        # a plated vehicle can still have a later sighting where ANPR fails;
        # that sighting should still attach to the known identity, not spawn
        # a new anonymous one).
        candidate, score = self._best_match_any(session, embedding, observed_at)
        if candidate is not None:
            gap_s = (observed_at - candidate.last_seen_at).total_seconds()
            candidate.last_seen_at = observed_at
            session.commit()
            return candidate, LinkInfo(method="appearance_match", score=score, time_gap_s=gap_s)

        identity = VehicleIdentity(first_seen_at=observed_at, last_seen_at=observed_at)
        identity.set_embedding(embedding)
        session.add(identity)
        session.commit()
        return identity, LinkInfo(method="new_identity")

    def _best_anonymous_match(
        self, session: Session, embedding: np.ndarray, observed_at: dt.datetime
    ) -> Tuple[Optional[VehicleIdentity], Optional[float]]:
        return self._best_match(session, embedding, observed_at, plate_is_null=True)

    def _best_match_any(
        self, session: Session, embedding: np.ndarray, observed_at: dt.datetime
    ) -> Tuple[Optional[VehicleIdentity], Optional[float]]:
        return self._best_match(session, embedding, observed_at, plate_is_null=None)

    def _best_match(
        self,
        session: Session,
        embedding: np.ndarray,
        observed_at: dt.datetime,
        plate_is_null: Optional[bool],
    ) -> Tuple[Optional[VehicleIdentity], Optional[float]]:
        cutoff = observed_at - ASSOCIATION_WINDOW
        query = session.query(VehicleIdentity).filter(VehicleIdentity.last_seen_at >= cutoff)
        if plate_is_null is True:
            query = query.filter(VehicleIdentity.plate.is_(None))

        best, best_score = None, EMBEDDING_SIMILARITY_THRESHOLD
        for identity in query.all():
            other = identity.get_embedding()
            if other is None:
                continue
            score = cosine_similarity(embedding, other)
            if score > best_score:
                best, best_score = identity, score
        return best, (best_score if best is not None else None)


identity_resolver = IdentityResolver()
