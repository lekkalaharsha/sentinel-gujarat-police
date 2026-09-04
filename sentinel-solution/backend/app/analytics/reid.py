"""Vehicle appearance embedding — the fallback identity when ANPR fails.

`ColorHistogramEncoder` is deliberately not a stub: no dependencies beyond
OpenCV/numpy, and it's real enough to distinguish "white SUV" from "red
hatchback" across cameras, which is exactly what's needed for the
anonymous-track-association use case (see identity.py). It is not
state-of-the-art vehicle re-ID — FastReID/OSNet pretrained on VeRi-776 is
the documented real upgrade once training/deployment time allows (see
STRATEGY.md) — but it is genuinely functional today, unlike a stub that
returns zeros.
"""
from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

EMBEDDING_DIM = 32 + 16  # HSV hist bins + grayscale template cells


class ReIdEncoder(Protocol):
    def encode(self, vehicle_crop: np.ndarray) -> np.ndarray: ...


class ColorHistogramEncoder:
    """Concatenates a coarse HSV colour histogram (appearance) with a small
    resized-grayscale template (rough shape/silhouette), L2-normalized.
    Cosine similarity between two embeddings is a reasonable proxy for
    "probably the same vehicle" across cameras with different angles."""

    def encode(self, vehicle_crop: np.ndarray) -> np.ndarray:
        if vehicle_crop.size == 0:
            return np.zeros(EMBEDDING_DIM, dtype=np.float32)

        hsv = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 2], [0, 180, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()  # 32 values

        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        template = cv2.resize(gray, (4, 4), interpolation=cv2.INTER_AREA).flatten() / 255.0  # 16 values

        embedding = np.concatenate([hist, template]).astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding


class FastReIdEncoder:
    """Real pretrained vehicle re-ID (FastReID/OSNet on VeRi-776). Lazily
    imported — requires model weights not bundled here. See STRATEGY.md."""

    def __init__(self, weights_path: str):
        raise NotImplementedError(
            "FastReID integration requires model weights and the fastreid "
            "package; wire this in once training/deployment time allows. "
            "ColorHistogramEncoder is the working default until then."
        )

    def encode(self, vehicle_crop: np.ndarray) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.size == 0 or b.size == 0:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
