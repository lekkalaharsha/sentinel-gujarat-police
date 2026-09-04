"""Two-stage plate localization: don't run OCR on the full vehicle crop.

vehicle crop -> plate region -> perspective/contrast enhancement -> OCR

Running OCR directly on a whole vehicle (bumper, badges, background text)
produces far more false positives than localizing the plate region first.
`StubPlateDetector` is honest about the gap: no open-source model reads
Indian plates well out of the box (see anpr.py), and the same is true for
plate *localization* — a fine-tuned YOLOv8 plate detector (trained on an
Indian plate dataset) is the documented real upgrade (see STRATEGY.md); the
stub instead uses a simple heuristic crop of the vehicle's lower-middle
region, which is where a plate usually sits, so the pipeline still runs
end-to-end without extra model weights.
"""
from __future__ import annotations

from typing import Optional, Protocol, Tuple

import cv2
import numpy as np

BBox = Tuple[int, int, int, int]


class PlateDetector(Protocol):
    def locate(self, vehicle_crop: np.ndarray) -> Optional[BBox]: ...


class StubPlateDetector:
    """Heuristic: plates sit in the lower-middle third of a vehicle crop.
    Crude, but better than feeding OCR the whole vehicle (headlights,
    grille badges, reflections)."""

    def locate(self, vehicle_crop: np.ndarray) -> Optional[BBox]:
        h, w = vehicle_crop.shape[:2]
        if h < 10 or w < 10:
            return None
        x1 = int(w * 0.2)
        x2 = int(w * 0.8)
        y1 = int(h * 0.55)
        y2 = int(h * 0.95)
        return (x1, y1, x2, y2)


class YoloPlateDetector:
    """Real implementation: a YOLO model fine-tuned specifically for plate
    localization (not the general vehicle detector). Lazily imported.
    Requires separately trained/downloaded weights — see STRATEGY.md."""

    def __init__(self, weights: str, conf_threshold: float = 0.35):
        from ultralytics import YOLO  # noqa: PLC0415

        self._model = YOLO(weights)
        self._conf_threshold = conf_threshold

    def locate(self, vehicle_crop: np.ndarray) -> Optional[BBox]:
        results = self._model.predict(vehicle_crop, verbose=False, conf=self._conf_threshold)
        best_box, best_conf = None, 0.0
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    best_box, best_conf = (int(x1), int(y1), int(x2), int(y2)), conf
        return best_box


def crop_plate(vehicle_crop: np.ndarray, bbox: BBox) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h, w = vehicle_crop.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    return vehicle_crop[y1:y2, x1:x2]


def enhance_plate_crop(plate_crop: np.ndarray) -> np.ndarray:
    """Real, dependency-free enhancement: grayscale + CLAHE contrast
    normalization + upscaling. Meaningfully improves OCR hit rate on small/
    low-contrast plate crops without needing a perspective-correction model
    (no reliable open-source Indian-plate corner detector exists — see
    STRATEGY.md; this is the honest, working substitute for that stage)."""
    if plate_crop.size == 0:
        return plate_crop
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if plate_crop.ndim == 3 else plate_crop
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    h, w = enhanced.shape[:2]
    scale = max(1, 200 // max(w, 1))
    if scale > 1:
        enhanced = cv2.resize(enhanced, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
