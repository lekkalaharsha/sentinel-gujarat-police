"""Pluggable vehicle/object detection.

Swap `StubVehicleDetector` for a real model (e.g. YOLOv8 via `ultralytics`)
by implementing the same `VehicleDetector` interface — nothing else in the
pipeline needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

import numpy as np


@dataclass
class Detection:
    label: str  # "car", "truck", "motorcycle", "person", ...
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2) in pixels
    # Real ByteTrack ID (see YoloVehicleDetector) when the detector performs
    # tracking, not just per-frame detection. None for the stub, or for a
    # detection ByteTrack hasn't confirmed into a track yet — callers must
    # fall back to IOU association in that case (see tracker.py).
    track_id: Optional[int] = None


class VehicleDetector(Protocol):
    def detect(self, image: np.ndarray) -> List[Detection]: ...


class StubVehicleDetector:
    """No-op placeholder so the pipeline runs end-to-end without GPU/model
    weights. Replace with a real model before evaluation — see README."""

    def detect(self, image: np.ndarray) -> List[Detection]:
        return []


class YoloVehicleDetector:
    """Real implementation, lazily imports `ultralytics` so the rest of the
    service works even if it isn't installed yet.

    Usage:
        detector = YoloVehicleDetector(weights="yolov8n.pt")

    Uses Ultralytics' built-in ByteTrack (`model.track(..., persist=True)`)
    rather than bare `.predict()`, so each `Detection` carries a real
    cross-frame track ID — this closes the "ByteTrack not implemented" gap
    documented in HLD.md, using a tracker already shipped in the
    `ultralytics` dependency we have, not a new model/weights download.

    IMPORTANT: `persist=True` keeps tracker state (lost-track buffers, ID
    counter) on `self._model`. That state is only meaningful for a single,
    continuous camera stream — one instance must not be shared across
    concurrent cameras, or tracks from different physical scenes would
    associate with each other. See `AnalyticsPipeline`, which builds one
    instance per camera_id for exactly this reason.
    """

    VEHICLE_LABELS = {"car", "truck", "bus", "motorcycle"}

    def __init__(self, weights: str = "yolov8n.pt", conf_threshold: float = 0.4):
        from ultralytics import YOLO  # noqa: PLC0415 — intentional lazy import

        self._model = YOLO(weights)
        self._conf_threshold = conf_threshold

    def detect(self, image: np.ndarray) -> List[Detection]:
        results = self._model.track(
            image, persist=True, tracker="bytetrack.yaml", verbose=False, conf=self._conf_threshold
        )
        out: List[Detection] = []
        for r in results:
            names = r.names
            for box in r.boxes:
                label = names[int(box.cls[0])]
                if label not in self.VEHICLE_LABELS and label != "person":
                    continue
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                # box.id is None when ByteTrack hasn't confirmed this
                # detection into a track yet (e.g. its first frame) — the
                # caller (tracker.py) falls back to IOU association for
                # those, same as before this change.
                track_id = int(box.id[0]) if box.id is not None else None
                out.append(Detection(label, float(box.conf[0]), (x1, y1, x2, y2), track_id=track_id))
        return out
