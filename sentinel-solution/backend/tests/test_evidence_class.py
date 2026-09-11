"""Regression coverage for analytics/evidence_class.py.

These assertions are the product rule, not implementation detail: an
appearance-only link must never become exportable evidence (CLAUDE.md 5.2,
and DECISION_REVIEW_2026-09-11.md's 41.87% false-positive measurement).
"""
from __future__ import annotations

import pytest

from app.analytics.evidence_class import (
    CONFIRMED,
    LEAD_ONLY,
    PROBABLE,
    classify,
    describe,
    is_exportable,
)


@pytest.mark.parametrize(
    "plate,link_method,expected",
    [
        ("GJ01AB1234", "new_identity", CONFIRMED),
        ("GJ01AB1234", "appearance_match", CONFIRMED),  # own read outranks a weak link
        (None, "plate_continuation", PROBABLE),
        (None, "plate_upgrade", PROBABLE),
        (None, "appearance_match", LEAD_ONLY),
        (None, "new_identity", LEAD_ONLY),
        (None, None, LEAD_ONLY),
    ],
)
def test_classification(plate, link_method, expected):
    assert classify(plate, link_method) == expected


def test_only_confirmed_is_exportable():
    assert is_exportable(CONFIRMED) is True
    assert is_exportable(PROBABLE) is False
    assert is_exportable(LEAD_ONLY) is False


def test_an_appearance_only_sighting_is_never_exportable():
    """The single rule this module exists to enforce."""
    assert is_exportable(classify(None, "appearance_match")) is False


def test_a_plate_read_at_this_camera_is_always_confirmed():
    """A stored plate already passed PLATE_PATTERN and PLATE_MIN_CONFIDENCE,
    so it must not be downgraded by a weak link method."""
    for method in ("new_identity", "plate_continuation", "plate_upgrade", "appearance_match", None):
        assert classify("GJ27ED1763", method) == CONFIRMED


def test_anonymous_and_appearance_leads_get_different_reasons():
    """Both are LEAD_ONLY but an investigator needs to know which — an
    unexplained badge is what this project is trying to avoid."""
    appearance = describe(LEAD_ONLY, "appearance_match")
    anonymous = describe(LEAD_ONLY, "new_identity")
    assert appearance != anonymous
    assert "appearance similarity" in appearance
    assert "anonymous observation" in anonymous


def test_every_class_has_a_reason_string():
    for cls in (CONFIRMED, PROBABLE, LEAD_ONLY):
        assert describe(cls, "appearance_match").strip()


def test_whitespace_only_plate_is_not_treated_as_a_read():
    """A whitespace-only string is truthy in Python but is not a validated
    read — anpr.py's PLATE_PATTERN would reject it before it ever reaches
    the DB, but classify() must not rely on that invariant holding forever."""
    assert classify("   ", "appearance_match") == LEAD_ONLY
    assert classify("\t\n", "new_identity") == LEAD_ONLY


def test_empty_string_plate_falls_through_to_link_method_not_confirmed():
    """An empty plate string is falsy already, so this locks in the correct
    behaviour (falls through to the link_method check) rather than the bug
    this test originally (incorrectly) asserted against."""
    assert classify("", "plate_continuation") == PROBABLE
    assert classify("", "appearance_match") == LEAD_ONLY


def test_unrecognised_link_method_falls_through_to_lead_only():
    """A future link_method nobody has written a rule for yet must default
    to the most conservative class, never PROBABLE or CONFIRMED."""
    assert classify(None, "some_future_method_nobody_wrote_yet") == LEAD_ONLY
    assert classify(None, "Plate_Continuation") == LEAD_ONLY  # case mismatch is unrecognised, not a typo-tolerant match


def test_classification_takes_no_score_argument():
    """The single most important structural guarantee: classify() cannot see
    link_score or a fused UI confidence at all, so a high score can never
    upgrade a class — the signature itself is the enforcement."""
    import inspect
    params = list(inspect.signature(classify).parameters)
    assert params == ["plate", "link_method"]


def test_all_four_real_link_methods_are_handled_deliberately():
    """The exhaustive set of link_method values identity.py actually writes
    (see analytics/identity.py's LinkInfo.method docstring) — each must
    resolve through an explicit branch, not an accidental fallthrough."""
    assert classify("GJ01AB1234", "new_identity") == CONFIRMED
    assert classify(None, "new_identity") == LEAD_ONLY
    assert classify(None, "plate_continuation") == PROBABLE
    assert classify(None, "plate_upgrade") == PROBABLE
    assert classify(None, "appearance_match") == LEAD_ONLY
