"""Resilient RTSP consumer for a single camera.

Encodes every rule from the "Consuming the Sentinel Camera Grid" guide:

- Forces RTSP over TCP (never UDP).
- Never trusts CAP_PROP_FPS; all timing is derived from PTS
  (CAP_PROP_POS_MSEC), never wall-clock arrival time.
- Tolerates non-uniform inter-frame gaps without treating them as a
  disconnect.
- Reconnects with exponential backoff (2s -> 30s cap), never a tight loop.
- Logs decoder warnings at join instead of aborting on them.
- Detects a scene discontinuity (PTS jumps backward, i.e. the feed looped)
  and emits a callback so downstream trackers can reset per-camera state
  instead of computing impossible velocities across the cut.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import cv2

from .. import config

logger = logging.getLogger("sentinel.rtsp")

# Must be set before cv2.VideoCapture is constructed.  `stimeout` is an
# FFmpeg socket I/O timeout in microseconds; without it a stalled TCP peer can
# hold cap.read() forever and bypass our failure/backoff path.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    f"rtsp_transport;tcp|stimeout;{config.RTSP_READ_TIMEOUT_US}",
)


@dataclass
class Frame:
    camera_id: str
    image: "cv2.Mat"
    pts_ms: float
    discontinuity: bool  # True if this frame follows a scene loop / hard cut


FrameHandler = Callable[[Frame], None]


class RtspCameraWorker:
    """Runs in its own thread; owns one VideoCapture for one camera."""

    def __init__(self, camera_id: str, rtsp_url: str, on_frame: FrameHandler):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self._on_frame = on_frame
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Health-monitoring state (Model 1 deliverable — see api/routes_cameras.py
        # and main.py's health-sync loop). Plain bool/float writes from one
        # producer thread, read by others; fine without a lock for this
        # coarse periodic-polling use, same tradeoff as StreamManager already
        # makes elsewhere.
        self.connected: bool = False
        self.last_frame_at: Optional[float] = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name=f"rtsp-{self.camera_id}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        # DO — pace your load: close captures you're finished with.
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        delay = config.RECONNECT_INITIAL_DELAY_S
        last_pts_ms: Optional[float] = None

        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                logger.warning("camera %s: failed to open, retrying in %.1fs", self.camera_id, delay)
                cap.release()
                self._sleep_backoff(delay)
                delay = min(delay * config.RECONNECT_BACKOFF_FACTOR, config.RECONNECT_MAX_DELAY_S)
                continue

            logger.info("camera %s: connected", self.camera_id)
            delay = config.RECONNECT_INITIAL_DELAY_S  # reset backoff on success
            consecutive_read_failures = 0
            self.connected = True
            # A fresh cv2.VideoCapture is a new stream from the downstream
            # tracker's point of view even though last_pts_ms was cleared
            # below on the previous disconnect — force the FIRST frame after
            # every (re)connect to report discontinuity=True so pipeline.py
            # resets per-camera tracker/ByteTrack state instead of computing
            # a track continuation across the reconnect gap. Without this,
            # last_pts_ms being None made the discontinuity check silently
            # False on exactly the frame that most needed it flagged.
            just_reconnected = True

            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    consecutive_read_failures += 1
                    # A handful of transient decode warnings at join/mid-stream
                    # is expected (H.264/H.265 IDR wait) — not fatal. Only
                    # treat a sustained failure run as a real disconnect.
                    if consecutive_read_failures < 15:
                        continue
                    logger.info("camera %s: stream ended/disconnected, reconnecting", self.camera_id)
                    break

                consecutive_read_failures = 0
                self.last_frame_at = time.time()
                pts_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                # Scene discontinuity detection: the sandbox loops each
                # recording, which looks like PTS resetting/jumping backward.
                discontinuity = just_reconnected or (last_pts_ms is not None and pts_ms < last_pts_ms)
                just_reconnected = False
                last_pts_ms = pts_ms

                try:
                    self._on_frame(Frame(self.camera_id, frame, pts_ms, discontinuity))
                except Exception:  # noqa: BLE001 — a bad frame must not kill the reader
                    logger.exception("camera %s: frame handler error", self.camera_id)

            cap.release()
            last_pts_ms = None
            self.connected = False
            if not self._stop.is_set():
                self._sleep_backoff(delay)
                delay = min(delay * config.RECONNECT_BACKOFF_FACTOR, config.RECONNECT_MAX_DELAY_S)

    def _sleep_backoff(self, delay: float) -> None:
        self._stop.wait(timeout=delay)
