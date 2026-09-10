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