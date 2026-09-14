"""Regression tests for analytics/tracker.py (SWE-4).

Guards the two failure modes found only by manual testing:
- `consensus_plate()` vote-share logic (conflicting OCR reads on one vehicle
  must collapse to the majority plate, with an honest confidence, never a
  stale single frame);
- the ByteTrack id-handoff fork: `box.id` is None on a detection's first
  frame and only assigned from frame 2, so an external-track-id branch that
  unconditionally created a new track split every vehicle into two
  disconnected tracks. The fix claims the frame-1 IOU-fallback track; these
  tests pin that behavior.
"""
from __future__ import annotations

import pytest
import numpy as np

from app.analytics.attributes import VehicleAttributes
from app.analytics.tracker import CameraTracker, _iou

ATTRS = VehicleAttributes(
    vehicle_type="car",
    color="white",
    color_confidence=0.75,
    width_px=100,
    height_px=60,
    aspect_ratio=1.67,
)

B = (10.0, 10.0, 50.0, 50.0)


# --- IOU --------------------------------------------------------------------

def test_iou_identical_boxes_is_one():
    assert _iou(B, B) == pytest.approx(1.0)


def test_iou_disjoint_boxes_is_zero():
    assert _iou(B, (60.0, 10.0, 100.0, 50.0)) == 0.0


# --- consensus_plate --------------------------------------------------------

def _single_track_with_reads(reads):
    """Drive one Track through CameraTracker.update with the given
    (plate, confidence) reads and return the track."""
    tracker = CameraTracker()
    track = None
    for i, (plate, conf) in enumerate(reads):
        track = tracker.update(
            bbox=B,
            pts_ms=1000.0 + i * 100,
            vehicle_type="car",
            detection_confidence=0.9,
            attrs=ATTRS,
            plate_result=(plate, conf),
        )
    assert track is not None
    return track


def test_consensus_plate_isolates_higher_vote_share():
    """A 0.9+0.85 majority over a stray 0.4 misread must win — and its
    confidence is the minority-diluted vote share (0.81), not a flat 1.0."""
    track = _single_track_with_reads([
        ("GJ01AB1234", 0.9),
        ("GJ01AB1234", 0.85),
        ("GJ01ZZ9999", 0.4),
    ])
    plate, conf = track.consensus_plate()
    assert plate == "GJ01AB1234"
    assert conf == pytest.approx(0.81, abs=0.01)


def test_consensus_plate_real_cam06_vehicle_clears_confidence_gate():
    """Real-world regression, not synthetic: the actual 5 OCR votes
    PaddleOCR produced for a real car on live sandbox camera cam06
    (2026-09-05 full re-scan, after the multi-line-plate/homoglyph fix in
    anpr.py), manually confirmed correct against the saved vehicle crop.
    Locks in that this specific real read clears PLATE_MIN_CONFIDENCE=0.5
    in the actual production consensus-vote logic — not just a script
    reproducing it once, ad hoc."""
    track = _single_track_with_reads([
        ("GJ01RP6128", 0.890240490436554),
        ("GU01RP6128", 0.850904107093811),  # one real misread of the 5
        ("GJ01RP6128", 0.8738139867782593),
        ("GJ01RP6128", 0.887633740901947),
        ("GJ01RP6128", 0.9249292612075806),
    ])
    plate, conf = track.consensus_plate()
    assert plate == "GJ01RP6128"
    assert conf == pytest.approx(0.81, abs=0.01)
    from app import config
    assert conf >= config.PLATE_MIN_CONFIDENCE


def test_consensus_plate_single_read_is_full_strength():
    track = _single_track_with_reads([("GJ01AB1234", 0.9)])
    plate, conf = track.consensus_plate()
    assert plate == "GJ01AB1234"
    assert conf == pytest.approx(1.0)


def test_consensus_plate_no_reads_returns_none():
    tracker = CameraTracker()
    track = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.9, attrs=ATTRS, plate_result=None,
    )
    assert track.consensus_plate() == (None, None)


def test_consensus_plate_confidence_is_vote_share_not_count():
    """Two votes for each of two plates: the confidence must be 0.5 (a split
    verdict), not 1.0 — this is what keeps a well-read-but-split vehicle from
    ever looking like a confident read."""
    track = _single_track_with_reads([
        ("GJ01AB1234", 0.9),
        ("GJ01AB1234", 0.9),
        ("GJ01ZZ9999", 0.9),
        ("GJ01ZZ9999", 0.9),
    ])
    plate, conf = track.consensus_plate()
    assert plate == "GJ01AB1234"  # first-inserted wins the tie
    assert conf == pytest.approx(0.5)


def test_consensus_plate_position_voting_recovers_read_exact_string_voting_would_fail():
    """The real gap this position-weighted rewrite fixes (TASKS.md,
    2026-09-05): 5 reads, each with a DIFFERENT single-character misread at
    a DIFFERENT position, so all 5 raw strings are distinct. The OLD
    exact-string algorithm would see 5 candidates with equal vote share
    (0.85/4.25 = 0.2 each) — below PLATE_MIN_CONFIDENCE=0.5, a rejected
    read despite every position having 4-out-of-5 real agreement. Per-
    character voting recovers the correct plate at 0.8 confidence, clearing
    the gate, because each position's majority survives independently of
    which OTHER position that same read got wrong."""
    true_plate = "GJ01RP6128"
    reads = []
    for wrong_pos in range(5):
        chars = list(true_plate)
        chars[wrong_pos] = "X"
        reads.append(("".join(chars), 0.85))
    track = _single_track_with_reads(reads)
    plate, conf = track.consensus_plate()
    assert plate == true_plate
    assert conf == pytest.approx(0.8)
    from app import config
    assert conf >= config.PLATE_MIN_CONFIDENCE


def test_consensus_plate_different_length_reads_grouped_separately():
    """A dropped/added-character OCR read (different length) must not be
    position-voted against the correct-length reads — it forms its own
    group, and the group with more total confidence wins."""
    track = _single_track_with_reads([
        ("GJ01AB1234", 0.9),
        ("GJ01AB1234", 0.85),
        ("GJ1AB1234", 0.95),  # one character short — a different group
    ])
    plate, conf = track.consensus_plate()
    assert plate == "GJ01AB1234"
    assert conf == pytest.approx(1.0)  # unanimous within its own (winning) group


# --- track-contamination: known, unmitigated limitation ---------------------

def test_consensus_plate_can_synthesize_a_string_that_matches_no_actual_read():
    """With reads from more than two sources, position voting can produce
    a full string matching NONE of them:
        pos0: 'A' mass=1.5 vs 'X' mass=2.5           -> 'X'
        pos1: 'B' mass=2.0 vs 'Z' 0.5, 'Y' 1.5        -> 'B'
        pos2: 'C' mass=1.5 vs 'Y' 1.0, 'Z' 1.5 (tie,
              first-seen wins)                        -> 'C'
    "XBC" appears in none of "ABC"/"XBY"/"AZC"/"XYZ" — see
    consensus_plate()'s docstring for why this isn't fixed here."""
    tracker = CameraTracker()
    track = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.9, attrs=ATTRS, plate_result=("ABC", 1.0),
    )
    track.add_observation(B, 1100.0, 0.9, ATTRS, ("XBY", 1.0))
    track.add_observation(B, 1200.0, 0.9, ATTRS, ("AZC", 0.5))
    track.add_observation(B, 1300.0, 0.9, ATTRS, ("XYZ", 1.5))

    plate, conf = track.consensus_plate()

    assert plate == "XBC"
    assert plate not in {"ABC", "XBY", "AZC", "XYZ"}
    assert conf == pytest.approx(0.38, abs=0.01)


def test_iou_overlap_with_visibly_different_crop_starts_a_new_track():
    """The contamination fixture must be prevented before OCR votes mix."""
    tracker = CameraTracker()
    dark = np.zeros((40, 40, 3), dtype=np.uint8)
    bright = np.full((40, 40, 3), 255, dtype=np.uint8)
    first = tracker.update(B, 1000.0, "car", 0.9, ATTRS, ("ABC", 0.9), crop=dark)
    second = tracker.update(B, 1100.0, "car", 0.9, ATTRS, ("XYZ", 0.9), crop=bright)
    assert second.track_id != first.track_id
    assert first.consensus_plate()[0] == "ABC"
    assert second.consensus_plate()[0] == "XYZ"


# --- ByteTrack id handoff ---------------------------------------------------

def test_bytetrack_id_handoff_claims_frame1_iou_track():
    """The regression: frame 1 has external_track_id=None (ByteTrack hasn't
    assigned an id yet), frame 2 arrives with the real id and the same bbox.
    Frame 2 must CLAIM frame 1's IOU track — same Track object, same
    track_id, plate data landed on one track — not fork into a second one."""
    tracker = CameraTracker()

    t_first = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.7, attrs=ATTRS, plate_result=None,
        external_track_id=None,
    )
    assert t_first.track_id == 1
    assert t_first.external_track_id is None

    t_second = tracker.update(
        bbox=B, pts_ms=1080.0, vehicle_type="car",
        detection_confidence=0.8, attrs=ATTRS,
        plate_result=("GJ01AB1234", 0.9),
        external_track_id=42,
    )

    assert t_second.track_id == t_first.track_id
    assert t_second.external_track_id == 42
    assert t_second.consensus_plate()[0] == "GJ01AB1234"


def test_bytetrack_id_with_nonoverlapping_bbox_gets_fresh_track():
    """A genuinely different vehicle (no IOU overlap) must NOT be absorbed
    into the frame-1 track even though its external id is 'new'."""
    tracker = CameraTracker()
    t1 = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.7, attrs=ATTRS, plate_result=None,
        external_track_id=None,
    )
    t2 = tracker.update(
        bbox=(200.0, 10.0, 240.0, 50.0), pts_ms=2000.0, vehicle_type="car",
        detection_confidence=0.8, attrs=ATTRS, plate_result=None,
        external_track_id=42,
    )
    assert t2.track_id != t1.track_id
    assert t2.external_track_id == 42


def test_distinct_external_track_ids_never_merge():
    tracker = CameraTracker()
    a = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.7, attrs=ATTRS, plate_result=None,
        external_track_id=1,
    )
    b = tracker.update(
        bbox=(200.0, 10.0, 240.0, 50.0), pts_ms=1050.0, vehicle_type="car",
        detection_confidence=0.7, attrs=ATTRS, plate_result=None,
        external_track_id=2,
    )
    assert a.track_id != b.track_id
    assert a.external_track_id == 1
    assert b.external_track_id == 2


# --- timeout ----------------------------------------------------------------

def test_pop_expired_only_finalizes_stale_tracks():
    tracker = CameraTracker()
    track = tracker.update(
        bbox=B, pts_ms=1000.0, vehicle_type="car",
        detection_confidence=0.7, attrs=ATTRS, plate_result=None,
        external_track_id=None,
    )
    # well within TRACK_TIMEOUT_MS (3000): still active
    assert tracker.pop_expired(1000.0 + 100) == []
    # beyond it: finalized exactly once
    assert tracker.pop_expired(1000.0 + 4000.0) == [track]
    assert tracker.pop_expired(1000.0 + 5000.0) == []
