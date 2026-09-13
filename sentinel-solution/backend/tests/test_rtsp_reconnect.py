"""Regression coverage for streaming/rtsp_client.py's reconnect handling.

Real bug found 2026-09-13 (independent review): after a reconnect, the
worker reset `last_pts_ms = None`, which made the discontinuity check
(`last_pts_ms is not None and pts_ms < last_pts_ms`) silently False on the
very first frame of the new connection -- exactly the frame that most
needs to tell pipeline.py to reset per-camera tracker/ByteTrack state. A
vehicle detected right before a disconnect and one detected right after
could be wrongly treated as the same continuing track, producing an
impossible cross-gap velocity/trajectory.

These tests drive RtspCameraWorker._run() directly against a fake
cv2.VideoCapture so no real network/RTSP server is needed.
"""
from __future__ import annotations

import time

import pytest

from app.streaming import rtsp_client
from app.streaming.rtsp_client import Frame, RtspCameraWorker


class _FakeCapture:
    """Simulates one cv2.VideoCapture connection. `frames_pts` is the
    sequence of PTS values this connection will yield before its stream
    "ends" (read() returns ok=False forever after)."""

    def __init__(self, frames_pts):
        self._frames_pts = list(frames_pts)
        self._opened = True
        self._read_failures_after_end = 0

    def isOpened(self):
        return self._opened

    def read(self):
        if self._frames_pts:
            pts = self._frames_pts.pop(0)
            return True, f"frame@{pts}"
        # Stream ended: fail reads until the worker's failure-threshold
        # (15) trips and it reconnects.
        self._read_failures_after_end += 1
        return False, None

    def get(self, prop):
        # Only CAP_PROP_POS_MSEC is used by the worker.
        return self._last_pts

    def release(self):
        self._opened = False

    def set_last_pts(self, pts):
        self._last_pts = pts


def test_first_frame_after_reconnect_is_flagged_as_discontinuity(monkeypatch):
    # Connection 1 yields pts 0, 100, 200 then "ends". Connection 2 (after
    # reconnect) yields pts 0, 100 -- a fresh recording, PTS restarts low,
    # which is NOT "less than" None so the buggy code never flagged it.
    connections = [
        _FakeCapture([0.0, 100.0, 200.0]),
        _FakeCapture([0.0, 100.0]),
    ]
    # Wire each fake capture's .get() to return its own popped pts by
    # wrapping read() to also stash the value .get() should report next.
    for cap in connections:
        orig_read = cap.read

        def make_read(cap=cap, orig_read=orig_read):
            def read():
                ok, val = orig_read()
                if ok:
                    pts = float(val.split("@")[1])
                    cap.set_last_pts(pts)
                return ok, val
            return read

        cap.read = make_read()

    connections_iter = iter(connections)

    class _NeverOpens:
        def isOpened(self):
            return False

        def release(self):
            pass

    def _next_capture(*_a, **_k):
        return next(connections_iter, _NeverOpens())

    monkeypatch.setattr(rtsp_client.cv2, "VideoCapture", _next_capture)
    monkeypatch.setattr(rtsp_client.time, "sleep", lambda *_a, **_k: None)

    received: list[Frame] = []
    worker = RtspCameraWorker("cam01", "rtsp://fake/stream", on_frame=received.append)

    # Make the "sustained failure" threshold and backoff sleep trivial so
    # the test doesn't need to wait through 15 failed reads / real backoff.
    monkeypatch.setattr(rtsp_client.config, "RECONNECT_INITIAL_DELAY_S", 0.0)
    monkeypatch.setattr(rtsp_client.config, "RECONNECT_BACKOFF_FACTOR", 1.0)
    monkeypatch.setattr(rtsp_client.config, "RECONNECT_MAX_DELAY_S", 0.0)
    # Speed up the worker's own backoff wait (uses a real threading.Event).
    monkeypatch.setattr(worker, "_sleep_backoff", lambda _delay: None)

    worker._thread = None
    worker._stop.clear()

    import threading

    t = threading.Thread(target=worker._run, daemon=True)
    t.start()
    # Wait until both connections have been fully drained and consumed.
    deadline = time.time() + 5
    while len(received) < 5 and time.time() < deadline:
        time.sleep(0.01)
    worker.stop()
    t.join(timeout=2)

    assert len(received) == 5, f"expected 5 frames across both connections, got {len(received)}"

    conn1_frames = received[:3]
    conn2_frames = received[3:]

    # Within connection 1: only the very first frame overall has no prior
    # PTS to compare against, so it is NOT a "discontinuity" by the PTS-jump
    # rule, but IS the first frame after the initial connect.
    assert conn1_frames[0].discontinuity is True  # first frame of the run
    assert conn1_frames[1].discontinuity is False
    assert conn1_frames[2].discontinuity is False

    # The bug: the first frame of connection 2 (post-reconnect) must be
    # flagged, even though its PTS (0.0) does not look like a backward jump
    # from a cleared last_pts_ms.
    assert conn2_frames[0].discontinuity is True, (
        "first frame after reconnect must report discontinuity=True so "
        "pipeline.py resets tracker state across the reconnect gap"
    )
    assert conn2_frames[1].discontinuity is False
