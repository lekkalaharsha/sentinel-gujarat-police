"""Regression coverage for api/rate_limit.py's FixedWindowLimiter."""
from __future__ import annotations

from app.api.rate_limit import EXEMPT_PATH_PREFIXES, FixedWindowLimiter


def test_allows_requests_under_the_limit():
    limiter = FixedWindowLimiter(limit=3, window_s=60.0)
    assert limiter.allow("key1") is True
    assert limiter.allow("key1") is True
    assert limiter.allow("key1") is True


def test_blocks_requests_over_the_limit_within_the_window():
    limiter = FixedWindowLimiter(limit=2, window_s=60.0)
    assert limiter.allow("key1") is True
    assert limiter.allow("key1") is True
    assert limiter.allow("key1") is False


def test_different_keys_have_independent_counters():
    limiter = FixedWindowLimiter(limit=1, window_s=60.0)
    assert limiter.allow("key1") is True
    assert limiter.allow("key2") is True  # not affected by key1's usage
    assert limiter.allow("key1") is False
    assert limiter.allow("key2") is False


def test_window_resets_after_it_elapses(monkeypatch):
    limiter = FixedWindowLimiter(limit=1, window_s=10.0)
    fake_time = [1000.0]
    monkeypatch.setattr("app.api.rate_limit.time.time", lambda: fake_time[0])

    assert limiter.allow("key1") is True
    assert limiter.allow("key1") is False  # still within the window

    fake_time[0] += 11.0  # past the 10s window
    assert limiter.allow("key1") is True


def test_health_and_live_paths_are_exempt():
    assert "/health" in EXEMPT_PATH_PREFIXES
    assert "/live/" in EXEMPT_PATH_PREFIXES
