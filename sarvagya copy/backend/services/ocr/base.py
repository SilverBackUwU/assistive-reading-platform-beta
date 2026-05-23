"""
services/ocr/base.py
====================
Abstract base class every OCR engine must implement.
The orchestrator calls .extract() on each engine — nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from schemas.ocr import LayerOutput


class OCREngine(ABC):
    """
    Contract: receive preprocessed image bytes, return LayerOutput.
    Never raises — catches internally and returns LayerOutput(success=False).
    """

    @abstractmethod
    async def extract(self, image_bytes: bytes) -> LayerOutput:
        """
        Args:
            image_bytes: preprocessed PNG bytes (already deskewed, binarized)
        Returns:
            LayerOutput with text + confidence, or success=False + error msg
        """
        ...

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Human-readable label, e.g. 'google', 'azure', 'gemini'"""
        ...
