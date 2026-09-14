"""Evidence classification for a single vehicle sighting.

Answers one question: how strongly is THIS sighting tied to the vehicle
identity an investigator searched for? That is the question that decides
whether a row may be exported as evidence, so it is derived here from
persisted decision-time provenance rather than assembled in the UI — a
label computed in the browser could drift from the data it describes, and
CLAUDE.md forbids letting a UI label turn inference into fact.

Derived, not stored: every input is already a column on VehicleEvent, so
this needs no migration and cannot disagree with the row it describes.

The three classes:

CONFIRMED  — this sighting carries its own plate read. By construction
             that read already passed anpr.py's PLATE_PATTERN gate and the
             PLATE_MIN_CONFIDENCE floor, so a stored plate is a validated
             plate.

PROBABLE   — no plate on this sighting, but it was attached to the identity
             by a plate-anchored method: same within-camera ByteTrack track
             as a sighting that did read a plate. The identity claim rests
             on within-camera track continuity, which is far stronger than
             appearance but is still not an independent read.

LEAD ONLY  — the identity claim rests on the appearance embedding, or on
             nothing at all (a standalone anonymous vehicle). The appearance
             encoder measured a 41.87% false-positive rate against real
             accumulated data (scripts/calibrate_embedding_threshold.py), so
             a link of this class is an investigative lead requiring human
             verification, never evidence. See DECISION_REVIEW_2026-09-11.md.
"""
from __future__ import annotations

CONFIRMED = "CONFIRMED"
PROBABLE = "PROBABLE"
LEAD_ONLY = "LEAD_ONLY"

# Only CONFIRMED may leave the system as evidence. PROBABLE is deliberately
# excluded too: it is a strong lead, but the sighting still never read the
# plate itself, and an export is the point where a hedge stops being visible.
EXPORTABLE_CLASSES = frozenset({CONFIRMED})

# link_method values that mean "a plate anchored this link", as written by
# analytics/identity.py at resolve time.
_PLATE_ANCHORED_METHODS = frozenset({"plate_continuation", "plate_upgrade"})

_REASONS = {
    CONFIRMED: "Plate read and validated at this camera.",
    PROBABLE: (
        "No plate read at this camera. Linked by within-camera track "
        "continuity from a sighting that did read the plate."
    ),
    LEAD_ONLY: (
        "No plate read at this camera. Linked by appearance similarity only "
        "— investigative lead requiring human verification, not evidence."
    ),
}

_ANONYMOUS_REASON = (
    "No plate read at this camera and no link to a prior sighting — an "
    "anonymous observation, not an identified vehicle."
)


def classify(plate: str | None, link_method: str | None) -> str:
    """Evidence class for one sighting. Inputs are VehicleEvent columns.

    `plate.strip()` rather than a bare truthiness check: a whitespace-only
    string is truthy in Python but is not a validated read. anpr.py's
    PLATE_PATTERN.fullmatch() already prevents that from reaching the DB
    through the real pipeline, but this function is the single gate that
    decides what may be exported — it must not rely on an upstream
    invariant holding forever (a manual fixture, a future migration, or a
    direct DB write could bypass anpr.py entirely). Fail conservative:
    treat anything that isn't a genuine non-blank string as no plate.
    An unrecognised link_method (a future value nobody has written a rule
    for yet) also falls through to LEAD_ONLY rather than PROBABLE or
    CONFIRMED — an unknown case must never be upgraded."""
    if plate and plate.strip():
        return CONFIRMED
    if link_method in _PLATE_ANCHORED_METHODS:
        return PROBABLE
    return LEAD_ONLY


def is_exportable(evidence_class: str) -> bool:
    return evidence_class in EXPORTABLE_CLASSES


def describe(evidence_class: str, link_method: str | None = None) -> str:
    """Investigator-facing reason for the class — shown next to the badge so
    the classification is never an unexplained label."""
    if evidence_class == LEAD_ONLY and link_method not in ("appearance_match",):
        return _ANONYMOUS_REASON
    return _REASONS[evidence_class]
