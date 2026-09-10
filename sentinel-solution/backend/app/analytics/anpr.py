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

import itertools
import re
from typing import Optional, Protocol, Tuple

import numpy as np

# Indian vehicle registration format, e.g. "GJ01AB1234"
PLATE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}")

# Common OCR digit/letter homoglyph confusions on small, low-contrast plate
# crops (found 2026-09-05 against a real two/three-wheeler plate at cam06:
# PaddleOCR read "GJOSA"+"Y6417" for an actual "GJ05AV6417" — 0 misread as O,
# 5 misread as S). Symmetric: doesn't assume which direction is "correct",
# just which characters get mistaken for each other either way.
_HOMOGLYPHS = {"O": "0", "0": "O", "S": "5", "5": "S", "I": "1", "1": "I",
               "B": "8", "8": "B", "Z": "2", "2": "Z"}


def _ambiguous_variants(candidate: str, max_flip_positions: int = 4):
    """Yields `candidate` itself, then variants with 1..N of its homoglyph
    -ambiguous characters flipped, cheapest (fewest flips) first. Bounded
    (max_flip_positions) so this stays a fast heuristic, not a combinatorial
    search — every variant is re-validated against the strict PLATE_PATTERN
    by the caller, so a bad flip just fails to match rather than producing
    a false plate silently; this only ever turns a REJECTED read into an
    ACCEPTED one, never the reverse."""
    yield candidate
    ambiguous_positions = [i for i, c in enumerate(candidate) if c in _HOMOGLYPHS]
    if not ambiguous_positions:
        return
    for n in range(1, min(len(ambiguous_positions), max_flip_positions) + 1):
        for combo in itertools.combinations(ambiguous_positions, n):
            chars = list(candidate)
            for i in combo:
                chars[i] = _HOMOGLYPHS[chars[i]]
            yield "".join(chars)


def _best_pattern_match(candidate: str) -> Optional[str]:
    """Strict match first; only tries homoglyph variants if the literal
    OCR output doesn't already validate. Returns the first (fewest-flips)
    variant that fullmatches, or None.

    Honest limitation (see tests/test_anpr.py): "fewest flips" is not the
    same as "most plausible plate" — this has no positional knowledge of
    which segment should be digits vs. letters, so it can return a
    technically-pattern-valid but real-world-unlikely correction (e.g.
    flipping only one of two ambiguous characters when flipping both would
    look more like a real RTO code). Good enough to gate "is this
    plate-SHAPED at all," not a guarantee of exact character accuracy —
    that's still what tracker.py's cross-frame consensus voting is for."""
    for variant in _ambiguous_variants(candidate):
        if PLATE_PATTERN.fullmatch(variant):
            return variant
    return None


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
        # Windows DLL-ordering guard: torch (imported by YoloVehicleDetector
        # via ultralytics) must load before paddlepaddle in this process, or
        # torch's native DLL loading breaks — reproduced empirically (see
        # HLD.md §8). Relying on every *caller* to construct the detector
        # before the plate reader is a real footgun (a caller can easily miss
        # it — this exact bug was caught by testing against the live sandbox,
        # not by inspection). Import torch defensively here as a self-healing
        # guard, regardless of construction order upstream. Safe if torch
        # isn't installed at all (ImportError swallowed) or already imported
        # (no-op).
        try:
            import torch  # noqa: F401, PLC0415
        except ImportError:
            pass

        from paddleocr import PaddleOCR  # noqa: PLC0415

        self._reader = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def read(self, vehicle_crop: np.ndarray) -> Optional[Tuple[str, float]]:
        results = self._reader.ocr(vehicle_crop, cls=True)
        best: Optional[Tuple[str, float]] = None
        detections = []  # (mean_y, text, conf) — collected for the multi-line join below

        for line in results or []:
            # When PaddleOCR finds no text at all in the image, it returns
            # `[None]` for that image, not `[]]` — confirmed against a real
            # blank-crop call, not assumed. Skip rather than crash.
            if not line:
                continue
            for box, (text, conf) in line:
                candidate = re.sub(r"[^A-Z0-9]", "", text.upper())
                matched = _best_pattern_match(candidate)
                if matched is not None and (best is None or conf > best[1]):
                    best = (matched, float(conf))
                mean_y = sum(pt[1] for pt in box) / len(box)
                detections.append((mean_y, candidate, float(conf)))

        if best is not None:
            return best

        # Two/three-wheeler plates are commonly TWO lines (e.g. "GJ05A" /
        # "V6417" for "GJ05AV6417") — PaddleOCR detects each line as its
        # own text region, so no single line ever fullmatches PLATE_PATTERN
        # on its own. Found 2026-09-05 against a real sandbox camera
        # (cam06): both lines read individually close-but-wrong
        # ("GJOSA"/"3Y6417"), neither matched alone, but the plate was
        # genuinely legible. Concatenating detections top-to-bottom (by
        # mean bounding-box y) and re-checking the JOINED string (with the
        # same homoglyph correction) recovers reads a single-line-only
        # check misses entirely. Skipped if there's only one detection —
        # that case is already covered by the per-line loop above.
        if len(detections) >= 2:
            detections.sort(key=lambda d: d[0])
            joined = "".join(d[1] for d in detections)
            matched = _best_pattern_match(joined)
            if matched is not None:
                # Conservative: a joined read is only as trustworthy as its
                # weakest line, not its strongest.
                joined_conf = min(d[2] for d in detections)
                return (matched, joined_conf)

        return None


def normalize_plate(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())
