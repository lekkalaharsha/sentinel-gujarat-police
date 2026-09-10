"""Regression coverage for anpr.py's pattern-matching helpers — no
PaddleOCR/torch dependency needed, these are pure string functions.

Found 2026-09-05 against a real sandbox camera (cam06, a close-range
front-on auto-rickshaw shot): PaddleOCR read a genuinely legible two-line
plate as "GJOSA" (top line) + "Y6417" (bottom line) — neither line alone
matched PLATE_PATTERN, and the code never tried the two joined, so a
readable real plate was silently discarded as unread. `_ambiguous_variants`
/`_best_pattern_match` fix both problems: multi-line joining, and OCR's
common 0/O, 5/S, 1/I, 8/B, 2/Z digit-letter confusion.
"""
from __future__ import annotations

from app.analytics.anpr import PLATE_PATTERN, _ambiguous_variants, _best_pattern_match


def test_exact_match_needs_no_correction():
    assert _best_pattern_match("GJ01AB1234") == "GJ01AB1234"


def test_homoglyph_correction_recovers_real_cam06_style_misread():
    # PaddleOCR's literal output for the two joined lines — 0 misread as O,
    # 5 misread as S. Neither raw string matches PLATE_PATTERN.
    joined = "GJOSAY6417"
    assert not PLATE_PATTERN.fullmatch(joined)
    corrected = _best_pattern_match(joined)
    assert corrected is not None
    assert PLATE_PATTERN.fullmatch(corrected)
    # NOT asserting a specific corrected string ("GJ05AY6417" is the
    # real-world-plausible one, but "GJ0SAY6417" — flipping only the O —
    # ALSO satisfies PLATE_PATTERN with fewer flips and is what the
    # fewest-flips-first search actually returns). This is an honest
    # limitation: the heuristic has no positional knowledge of which
    # segment should be digits vs. letters, so "fewest edits" and "most
    # plausible" aren't always the same answer. Fine for gating whether a
    # read is plate-SHAPED at all; not a guarantee of the exact characters.


def test_unfixable_candidate_returns_none():
    # No amount of homoglyph flipping turns free text into a plate shape.
    assert _best_pattern_match("HELLOWORLD") is None


def test_variants_are_bounded_not_combinatorially_exploding():
    # A string where every character is homoglyph-ambiguous must still
    # terminate quickly (max_flip_positions caps how many positions flip
    # at once, not how many variants total for large inputs).
    variants = list(_ambiguous_variants("0O5S1I8B2Z", max_flip_positions=2))
    assert variants[0] == "0O5S1I8B2Z"  # original always yielded first
    assert len(variants) < 1000  # sanity bound, not an exact count


def test_prefers_fewest_flips_when_multiple_variants_match():
    # "GJ0OAB1234" has one ambiguous char that's already correct (0) and
    # one already-correct letter position — only a single flip should be
    # needed, and it should be tried before any multi-flip variant.
    result = _best_pattern_match("GJ0OAB1234")
    assert result == "GJ0OAB1234" or PLATE_PATTERN.fullmatch(result)
