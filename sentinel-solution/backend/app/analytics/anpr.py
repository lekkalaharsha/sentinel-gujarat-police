"""Pluggable ANPR (Automatic Number Plate Recognition).

Same seam pattern as detector.py: `StubPlateReader` is a no-op so the
pipeline runs without extra dependencies; `PaddleOcrPlateReader` is a real,
open-source implementation to enable once weights/deps are installed.

`read()` returns `(plate, confidence)` rather than just a plate string —
the pipeline needs the confidence to decide whether to trust a single-frame
read outright or hold it for temporal fusion (see pipeline.py), and to log
it on VehicleEvent.plate_confidence either way.
"""
from __future__ import annotations

import re
from typing import Optional, Protocol, Tuple

import numpy as np

# Indian vehicle registration format, e.g. "GJ01AB1234"
PLATE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}")


class PlateReader(Protocol):
    def read(self, vehicle_crop: np.ndarray) -> Optional[Tuple[str, float]]: ...


class StubPlateReader:
    def read(self, vehicle_crop: np.ndarray) -> Optional[Tuple[str, float]]:
        return None


class PaddleOcrPlateReader:
    """Real implementation using PaddleOCR (open source, Apache 2.0, actively
    maintained — preferred over EasyOCR/Tesseract/OpenALPR for this project;
    see STRATEGY.md). Lazily imported.

    No open-source model reads Indian plates out of the box with high
    accuracy — this is the OCR stage of a pipeline whose Indian-plate
    specialization comes from the detector, PLATE_PATTERN validation below,
    and temporal fusion across frames (see pipeline.py), not from PaddleOCR
    itself.
    """

    def __init__(self, lang: str = "en"):
        from paddleocr import PaddleOCR  # noqa: PLC0415

        self._reader = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def read(self, vehicle_crop: np.ndarray) -> Optional[Tuple[str, float]]:
        results = self._reader.ocr(vehicle_crop, cls=True)
        best: Optional[Tuple[str, float]] = None
        for line in results or []:
            # When PaddleOCR finds no text at all in the image, it returns
            # `[None]` for that image, not `[]]` — confirmed against a real
            # blank-crop call, not assumed. Skip rather than crash.
            if not line:
                continue
            for _, (text, conf) in line:
                candidate = re.sub(r"[^A-Z0-9]", "", text.upper())
                if not PLATE_PATTERN.fullmatch(candidate):
                    continue
                if best is None or conf > best[1]:
                    best = (candidate, float(conf))
        return best


def normalize_plate(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())
