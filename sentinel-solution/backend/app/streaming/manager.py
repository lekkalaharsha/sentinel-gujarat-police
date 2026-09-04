"""Owns one RtspCameraWorker per active camera and wires frames into analytics.

- Reconciles workers against the live catalogue (open only what's live;
  close what's gone — "pace your load").
- Applies ANALYTICS_FRAME_STRIDE so heavy per-frame inference doesn't have
  to run on every frame of every camera.
"""
from __future__ import annotations

import logging
import threading
from typing import Dict

from .. import config
from ..catalogue import CatalogueClient
from .rtsp_client import Frame, RtspCameraWorker

logger = logging.getLogger("sentinel.stream-manager")

FrameSink = "callable(Frame) -> None"


class StreamManager:
    def __init__(self, catalogue: CatalogueClient, on_frame):
        self._catalogue = catalogue
        self._on_frame_downstream = on_frame
        self._workers: Dict[str, RtspCameraWorker] = {}
        self._frame_counters: Dict[str, int] = {}
        self._lock = threading.RLock()

    def _handle_frame(self, frame: Frame) -> None:
        with self._lock:
            n = self._frame_counters.get(frame.camera_id, 0) + 1
            self._frame_counters[frame.camera_id] = n
        if n % config.ANALYTICS_FRAME_STRIDE != 0:
            return
        self._on_frame_downstream(frame)

    def reconcile(self) -> None:
        """Call after every catalogue refresh."""
        live_cameras = {cid: cam for cid, cam in self._catalogue.cameras.items() if cam.live}

        with self._lock:
            current_ids = set(self._workers.keys())
            live_ids = set(live_cameras.keys())

            for cam_id in live_ids - current_ids:
                cam = live_cameras[cam_id]
                worker = RtspCameraWorker(cam.id, cam.rtsp_url, self._handle_frame)
                worker.start()
                self._workers[cam_id] = worker
                logger.info("started worker for camera %s (%s)", cam_id, cam.location)

            for cam_id in current_ids - live_ids:
                self._workers.pop(cam_id).stop()
                self._frame_counters.pop(cam_id, None)
                logger.info("stopped worker for camera %s (no longer live)", cam_id)

    def stop_all(self) -> None:
        with self._lock:
            for worker in self._workers.values():
                worker.stop()
            self._workers.clear()

    @property
    def active_camera_ids(self):
        with self._lock:
            return list(self._workers.keys())

    def health_snapshot(self) -> Dict[str, dict]:
        """Per-camera connection health — feeds the Model 1 'health
        monitoring' deliverable (see main.py's health-sync loop and
        api/routes_cameras.py's gap-analysis endpoint)."""
        with self._lock:
            return {
                cam_id: {"connected": w.connected, "last_frame_at": w.last_frame_at}
                for cam_id, w in self._workers.items()
            }
