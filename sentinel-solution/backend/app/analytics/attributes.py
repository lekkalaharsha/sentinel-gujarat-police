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

import cv2
import numpy as np

# Achromatic family (white/black/grey/silver): classified by normalized V
# only, in ascending-brightness order — hue is meaningless at low saturation
# so including it here would just be noise.
_ACHROMATIC_BANDS = [
    (60, "black"),
    (130, "grey"),
    (200, "silver"),
    (256, "white"),
]

# Chromatic family: (hue_lo, hue_hi, name) in OpenCV's 0-179 hue range: two
# entries for red since it wraps around 0/179.
_CHROMATIC_HUE_BANDS = [
    (0, 8, "red"),
    (8, 20, "orange"),
    (20, 35, "yellow"),
    (35, 85, "green"),
    (85, 130, "blue"),
    (130, 170, "red"),  # magenta/pink side of the wheel — closest bucket we have
    (170, 180, "red"),
]
# Low-value + orange/red hue reads as brown rather than a bright primary —
# distinguishes a brown car from a red one at the same hue.
_BROWN_VALUE_CEILING = 130


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


def _nearest_color_name(crop: np.ndarray, sample_stride: int = 4) -> tuple[str, float]:
    """HSV, saturation-gated, with V normalized against the crop's own
    brightness range — not a fixed-RGB nearest-neighbor. Real bug found by
    ML review 2026-09-04: comparing raw pixel values against fixed
    reference points is lighting-dependent by construction — a white car in
    shadow reads grey, silver under sodium-vapor lighting reads
    yellow/orange, both realistic for outdoor Gujarat traffic cameras.

    Two fixes:
    1. Saturation gate — hue is meaningless/noisy at low saturation, so
       white/black/grey/silver are classified by (normalized) brightness
       alone, never by hue. This is what actually rejects the sodium-vapor
       false-orange case: a genuinely orange PAINTED car has much higher
       saturation than a neutral surface under a warm colour-cast light.
    2. V normalized against the CROP's own min-max range (min-max
       contrast stretch, skipped if the crop has under 40 units of real
       brightness range — a near-uniform dark crop's "range" is just
       sensor noise, and normalizing against noise amplifies it into a
       false hue/saturation reading), not the absolute pixel value — a
       white car's body is still the brightest thing in its own crop
       whether the overall scene is in shadow or full sun, even though
       the absolute brightness differs a lot between those two scenes.

    Second honest limitation: normalizing V relative to the crop's own
    dark region (tires/shadow) correctly undoes a uniform shadow over the
    whole vehicle, but the SAME stretch can push a genuinely silver body
    into the "white" band, since white/silver differ only in absolute
    brightness — information relative normalization necessarily blurs.
    Verified directly: a realistic warm-cast silver crop stays in the
    achromatic family (the category-level fix that matters) but can land
    in "white" rather than "silver" — an adjacent-band mix-up, not the
    wrong colour family. Not chased further here; if it matters later, the
    fix is normalizing against a same-vehicle reference region (e.g. glass/
    roof) rather than tire-black, not a threshold tweak.

    Honest limitation, not fixed by this change: a STRONG colour cast
    (e.g. uncorrected sodium-vapor lighting at full strength) genuinely
    raises saturation enough to cross the achromatic gate — verified this
    boundary directly: a mild/realistic cast (S~27/255) is correctly kept
    achromatic, a strong cast (S~42+/255) is not. Distinguishing "silver
    under a strong warm light" from "actually orange paint" at that point
    is a color-constancy problem that needs real white-balance correction,
    not a bucketing threshold — out of scope here, and worth flagging
    rather than silently leaving unfixed.
    """
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    sampled = hsv[::sample_stride, ::sample_stride].reshape(-1, 3)
    h, s, v = np.median(sampled, axis=0)  # H(0-179), S(0-255), V(0-255)

    # Only stretch if the crop actually has enough internal brightness
    # range to normalize against (real bug, caught by testing: a genuinely
    # near-uniform dark crop — e.g. a black car — has a brightness range
    # of only a few units, all noise; dividing by that near-zero range
    # amplified sensor noise into an arbitrary hue/value swing instead of
    # a real signal. Below this floor, use the raw median V unscaled.)
    v_channel = hsv[..., 2].astype(np.float32)
    v_min, v_max = float(v_channel.min()), float(v_channel.max())
    v_norm = 255.0 * (float(v) - v_min) / (v_max - v_min) if (v_max - v_min) > 40 else float(v)

    # Saturation itself is unreliable at very low brightness — HSV's
    # saturation formula is (max-min)/max, so at low absolute pixel values
    # even a few units of sensor noise between channels reads as a large
    # RELATIVE swing (a near-black crop measured S=104/255 purely from
    # +/-6 gaussian noise in this session's own test, well above the
    # threshold below it). Gate on raw darkness too, not saturation alone.
    saturation_threshold = 40.0
    if s < saturation_threshold or v < 30.0:
        # Flat confidence for the achromatic family — the real gain here is
        # correctness (lighting-robust bucketing), not a graded score; a
        # fixed 0.75 is honest about that rather than implying more
        # precision than the bucketing actually has.
        for ceiling, name in _ACHROMATIC_BANDS:
            if v_norm < ceiling:
                return name, 0.75
        return "white", 0.75

    for lo, hi, name in _CHROMATIC_HUE_BANDS:
        if lo <= h < hi:
            if name == "red" and v_norm < _BROWN_VALUE_CEILING:
                return "brown", 0.6
            if name == "orange" and v_norm < _BROWN_VALUE_CEILING and s < 150:
                return "brown", 0.55
            # Higher saturation = more confident chromatic read.
            return name, round(min(1.0, s / 200.0), 2)
    return "grey", 0.3  # shouldn't happen — every hue is covered above


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
    color_name, color_conf = _nearest_color_name(vehicle_crop)
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
