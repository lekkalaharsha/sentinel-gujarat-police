"""Deliberately excluded face-recognition seam; it never returns a match."""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("sentinel.face_recognition")


class FaceRecognizer(Protocol):
    def identify(self, image): ...


class DeliberatelyExcludedFaceRecognizer:
    def identify(self, image):
        logger.warning("face recognition requested but deliberately excluded; see Model 4 ARCHITECTURE.md")
        raise RuntimeError("Face recognition is deliberately excluded from Sentinel")
