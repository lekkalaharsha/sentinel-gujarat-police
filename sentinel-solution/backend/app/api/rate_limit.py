"""Minimal in-process rate limiting — a fixed-window counter per API key
(or client IP if no key was sent), no new infrastructure (no Redis), sized
for this project's single-node pilot scale.

`/live/*` (HLS segment/playlist polling) and `/health` are exempt: those
are legitimately high-frequency and aren't the sensitive surface this
guards (search, watchlist, admin, and the key-check path itself).
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .. import config

EXEMPT_PATH_PREFIXES = ("/health", "/live/")


class FixedWindowLimiter:
    def __init__(self, limit: int, window_s: float = 60.0):
        self._limit = limit
        self._window_s = window_s
        self._lock = threading.Lock()
        self._counters: Dict[str, Tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            window_start, count = self._counters.get(key, (now, 0))
            if now - window_start >= self._window_s:
                window_start, count = now, 0
            count += 1
            self._counters[key] = (window_start, count)
            return count <= self._limit


_limiter = FixedWindowLimiter(limit=config.RATE_LIMIT_PER_MINUTE)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in EXEMPT_PATH_PREFIXES):
            return await call_next(request)
        client_key = request.headers.get("X-Sentinel-API-Key") or (
            request.client.host if request.client else "unknown"
        )
        if not _limiter.allow(client_key):
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        return await call_next(request)
