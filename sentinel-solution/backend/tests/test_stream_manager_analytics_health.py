"""Regression coverage for streaming/manager.py's analytics-liveness
tracking.

Real incident found 2026-09-13: a torch/torchvision ABI mismatch made
every analytics call raise, while RTSP connectivity (`connected`,
`last_frame_at`) stayed perfectly healthy the entire time. /health and
CameraRegistry.is_healthy reported "ok" with 30 active workers while
detection was 100% broken -- a real, live-reproduced instance of "health
monitoring only reflects stream connectivity, not analytics success".
These tests exercise StreamManager._handle_frame/health_snapshot directly
against a fake pipeline, without any real RTSP/ML dependency.
"""
from __future__ import annotations

import pytest

from app import config
from app.streaming.manager import ANALYTICS_DEGRADED_ERROR_THRESHOLD, StreamManager
from app.streaming.rtsp_client import Frame


class _FakeCatalogue:
    cameras = {}


def _frame(camera_id="cam01"):
    return Frame(camera_id=camera_id, image=None, pts_ms=0.0, discontinuity=False)


def test_camera_not_yet_processed_reports_not_degraded():
    manager = StreamManager(_FakeCatalogue(), on_frame=lambda f: None)
    manager._workers["cam01"] = type("W", (), {"connected": True, "last_frame_at": 1.0})()

    snapshot = manager.health_snapshot()

    assert snapshot["cam01"]["analytics_degraded"] is False
    assert snapshot["cam01"]["last_analytics_success_at"] is None


def test_successful_analytics_calls_never_flip_degraded(monkeypatch):
    monkeypatch.setattr(config, "ANALYTICS_FRAME_STRIDE", 1)
    calls = []
    manager = StreamManager(_FakeCatalogue(), on_frame=calls.append)
    manager._workers["cam01"] = type("W", (), {"connected": True, "last_frame_at": 1.0})()

    for _ in range(ANALYTICS_DEGRADED_ERROR_THRESHOLD + 2):
        manager._handle_frame(_frame())

    snapshot = manager.health_snapshot()
    assert len(calls) == ANALYTICS_DEGRADED_ERROR_THRESHOLD + 2
    assert snapshot["cam01"]["analytics_degraded"] is False
    assert snapshot["cam01"]["last_analytics_success_at"] is not None


def test_sustained_analytics_failures_flip_degraded_even_though_stream_connected(monkeypatch):
    """The exact bug shape: stream stays connected, but every analytics
    call raises (e.g. the real torch/torchvision mismatch). Must surface
    as degraded, not silently swallowed into an "ok" stream status."""
    monkeypatch.setattr(config, "ANALYTICS_FRAME_STRIDE", 1)

    def _boom(_frame):
        raise RuntimeError("operator torchvision::nms does not exist")

    manager = StreamManager(_FakeCatalogue(), on_frame=_boom)
    manager._workers["cam01"] = type("W", (), {"connected": True, "last_frame_at": 1.0})()

    for _ in range(ANALYTICS_DEGRADED_ERROR_THRESHOLD):
        with pytest.raises(RuntimeError):
            manager._handle_frame(_frame())

    snapshot = manager.health_snapshot()
    assert snapshot["cam01"]["connected"] is True  # the misleading-if-alone signal
    assert snapshot["cam01"]["analytics_degraded"] is True
    assert snapshot["cam01"]["last_analytics_success_at"] is None


def test_a_single_success_resets_the_consecutive_error_count(monkeypatch):
    """A transient failure (one bad frame) must not permanently mark a
    camera degraded once analytics resumes succeeding."""
    monkeypatch.setattr(config, "ANALYTICS_FRAME_STRIDE", 1)
    should_fail = [True] * (ANALYTICS_DEGRADED_ERROR_THRESHOLD - 1) + [False]

    def _flaky(_frame):
        if should_fail.pop(0):
            raise RuntimeError("transient")

    manager = StreamManager(_FakeCatalogue(), on_frame=_flaky)
    manager._workers["cam01"] = type("W", (), {"connected": True, "last_frame_at": 1.0})()

    for _ in range(ANALYTICS_DEGRADED_ERROR_THRESHOLD - 1):
        with pytest.raises(RuntimeError):
            manager._handle_frame(_frame())
    manager._handle_frame(_frame())  # the one success

    snapshot = manager.health_snapshot()
    assert snapshot["cam01"]["analytics_degraded"] is False
    assert snapshot["cam01"]["last_analytics_success_at"] is not None


def test_frame_stride_gates_which_frames_count_toward_analytics_health(monkeypatch):
    """Only every Nth frame actually reaches the analytics pipeline
    (ANALYTICS_FRAME_STRIDE) -- the skipped frames must not be counted as
    trivial "successes" that would mask a real analytics failure on the
    frames that do get processed."""
    monkeypatch.setattr(config, "ANALYTICS_FRAME_STRIDE", 3)
    calls = []
    manager = StreamManager(_FakeCatalogue(), on_frame=calls.append)
    manager._workers["cam01"] = type("W", (), {"connected": True, "last_frame_at": 1.0})()

    for _ in range(2):
        manager._handle_frame(_frame())  # frames 1, 2: stride-skipped

    assert calls == []
    snapshot = manager.health_snapshot()
    assert snapshot["cam01"]["analytics_degraded"] is False
    assert snapshot["cam01"]["last_analytics_success_at"] is None  # nothing actually ran yet

    manager._handle_frame(_frame())  # frame 3: reaches the pipeline
    assert len(calls) == 1
    assert manager.health_snapshot()["cam01"]["last_analytics_success_at"] is not None
