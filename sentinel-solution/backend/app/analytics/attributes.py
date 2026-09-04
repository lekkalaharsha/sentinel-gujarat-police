"""Vehicle attribute extraction: colour, type, and pixel dimensions.

These attributes matter for two reasons:
1. They're what a real APB/watchlist actually describes ("white Swift,
   partial plate GJ01AB...") — not just a plate string.
2. They're the fallback identifier when ANPR fails outright (bad angle,
   glare, mud, motion blur) — see routes_vehicle.py's search-by-attributes
   endpoint, which lets an investigator search on colour+type+route even
   with no readable plate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

# Coarse colour buckets — enough to be useful in an APB, not a paint-code match.
_NAMED_COLORS = {
    "white": (245, 245, 245),
    "black": (20, 20, 20),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "red": (180, 30, 30),
    "blue": (30, 60, 160),
    "yellow": (220, 200, 40),
    "green": (40, 120, 60),
    "brown": (110, 70, 40),
    "orange": (220, 120, 40),
}


@dataclass
class VehicleAttributes:
    vehicle_type: str  # from the detector's label: car/truck/bus/motorcycle
    color: str  # nearest named colour bucket
    color_confidence: float
    width_px: int
    height_px: int
    aspect_ratio: float
    make_model: Optional[str] = None  # left unset — see MakeModelClassifier below
    make_model_confidence: Optional[float] = None


def _dominant_bgr(crop: np.ndarray, sample_stride: int = 4) -> np.ndarray:
    """Cheap dominant-colour estimate: median of a strided pixel sample.
    Avoids extra ML dependencies (no k-means/sklearn needed) and is fast
    enough to run on every detection."""
    sampled = crop[::sample_stride, ::sample_stride].reshape(-1, 3)
    return np.median(sampled, axis=0)  # BGR, since frames come from OpenCV


def _nearest_color_name(bgr: np.ndarray) -> tuple[str, float]:
    b, g, r = bgr
    rgb = np.array([r, g, b], dtype=np.float32)
    best_name, best_dist = None, float("inf")
    for name, ref_rgb in _NAMED_COLORS.items():
        dist = float(np.linalg.norm(rgb - np.array(ref_rgb, dtype=np.float32)))
        if dist < best_dist:
            best_name, best_dist = name, dist
    # Convert distance to a rough 0-1 confidence (max plausible distance ~441 for RGB)
    confidence = max(0.0, 1.0 - best_dist / 441.0)
    return best_name, confidence


class MakeModelClassifier(Protocol):
    def classify(self, vehicle_crop: np.ndarray) -> tuple[Optional[str], Optional[float]]: ...


class StubMakeModelClassifier:
    """No open-source model reliably classifies vehicle make/model for
    Indian traffic out of the box (closest public datasets — Stanford Cars,
    CompCars — are US/China-market and would need retraining/fine-tuning on
    Indian vehicle data). Left as an explicit gap rather than a fake result;
    see STRATEGY.md."""

    def classify(self, vehicle_crop: np.ndarray) -> tuple[Optional[str], Optional[float]]:
        return None, None


def extract_attributes(
    vehicle_crop: np.ndarray,
    vehicle_type: str,
    make_model_classifier: MakeModelClassifier,
) -> VehicleAttributes:
    height_px, width_px = vehicle_crop.shape[:2]
    color_name, color_conf = _nearest_color_name(_dominant_bgr(vehicle_crop))
    make_model, mm_conf = make_model_classifier.classify(vehicle_crop)
    return VehicleAttributes(
        vehicle_type=vehicle_type,
        color=color_name,
        color_confidence=round(color_conf, 2),
        width_px=width_px,
        height_px=height_px,
        aspect_ratio=round(width_px / height_px, 2) if height_px else 0.0,
        make_model=make_model,
        make_model_confidence=mm_conf,
    )
