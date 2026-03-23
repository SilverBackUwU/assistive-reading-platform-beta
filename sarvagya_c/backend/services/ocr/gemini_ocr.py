"""
services/ocr/gemini_ocr.py
===========================
Layer 3 — Gemini 2.5 Flash.
Package: google-generativeai==0.8.3

Two roles:
  1. Standard OCR  → extract() called in parallel with L1 + L2
  2. Arbiter       → arbitrate() called when L1 and L2 disagree on a token

Auth: GEMINI_API_KEY from .env
Get key: aistudio.google.com → Get API Key (free, 1500 req/day)
"""
from __future__ import annotations

import json
import logging
import base64

from schemas.ocr import LayerOutput, OCREngineLabel
from services.ocr.base import OCREngine

logger = logging.getLogger(__name__)

# ── OCR system prompt ─────────────────────────────────────────────────────────
_OCR_PROMPT = """You are an expert Sanskrit OCR system.
Extract ALL text from this image exactly as it appears.
The script is Devanagari. The language is Sanskrit (or Hindi).
Rules:
- Preserve every character, space, punctuation mark, and danda (।)
- Do NOT translate, transliterate, or correct anything
- Do NOT add any explanation, preamble, or markdown
- Return ONLY the raw extracted text"""

# ── Arbiter system prompt ─────────────────────────────────────────────────────
_ARBITER_PROMPT = """You are a Sanskrit language expert and OCR arbiter.
You will receive an image and two OCR outputs that disagree on specific words.
Your task:
1. Look at the image for each conflicting region
2. Apply Sanskrit grammar, sandhi rules, and conjunct knowledge
3. Return ONLY valid JSON — no preamble, no markdown fences

Output format:
[
  {"index": 0, "chosen": "word", "confidence": 0.92, "reason": "brief"},
  ...
]

Rules:
- Prefer readings that form valid Sanskrit words or compounds
- Standard conjuncts: क्ष त्र ज्ञ श्र द्ध are very common — recognise them
- If genuinely ambiguous: return "ambiguous" as chosen with confidence 0.5
- reason field: max 8 words"""


class GeminiOCR(OCREngine):
    """
    Layer 3: Gemini 2.5 Flash as OCR engine AND conflict arbiter.
    Vision capability lets it both read text AND reason about it.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int):
        self._api_key = api_key
        self._model = model         # "gemini-2.5-flash"
        self._max_tokens = max_tokens
        self._client = None

    @property
    def engine_name(self) -> str:
        return OCREngineLabel.GEMINI

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(
                    model_name=self._model,
                    generation_config={
                        "max_output_tokens": self._max_tokens,
                        "temperature": 0.0,   # deterministic — critical for OCR
                    },
                )
                logger.info(f"Gemini client initialised: {self._model}")
            except Exception as e:
                raise RuntimeError(
                    f"Gemini client failed to initialise: {e}\n"
                    f"Check GEMINI_API_KEY in .env"
                ) from e
        return self._client

    async def extract(self, image_bytes: bytes) -> LayerOutput:
        """Standard OCR pass — called in parallel with Google + Azure."""
        try:
            import google.generativeai as genai

            client = self._get_client()

            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }

            response = client.generate_content(
                [_OCR_PROMPT, image_part]
            )

            text = response.text.strip() if response.text else ""

            if not text:
                return LayerOutput(
                    engine=OCREngineLabel.GEMINI,
                    text="",
                    confidence=0.0,
                    success=False,
                    error="Gemini returned empty text",
                )

            logger.info(f"Gemini OCR: {len(text)} chars")
            return LayerOutput(
                engine=OCREngineLabel.GEMINI,
                text=text,
                confidence=0.88,  # Gemini doesn't expose token-level confidence
                success=True,
            )

        except Exception as e:
            logger.error(f"Gemini OCR failed: {e}")
            return LayerOutput(
                engine=OCREngineLabel.GEMINI,
                text="",
                confidence=0.0,
                success=False,
                error=str(e),
            )

    async def arbitrate(
        self,
        image_bytes: bytes,
        conflicts: list[dict],
    ) -> list[dict]:
        """
        Called by consensus engine when all 3 engines disagree on a token.

        Args:
            image_bytes: the original preprocessed image
            conflicts: [{"index": int, "alternatives": ["w1","w2","w3"]}, ...]

        Returns:
            [{"index": int, "chosen": str, "confidence": float, "reason": str}, ...]
        """
        if not conflicts:
            return []

        try:
            client = self._get_client()

            conflict_text = json.dumps(conflicts, ensure_ascii=False, indent=2)
            prompt = (
                f"{_ARBITER_PROMPT}\n\n"
                f"Conflicting words to resolve:\n{conflict_text}"
            )

            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }

            response = client.generate_content([prompt, image_part])
            raw = response.text.strip() if response.text else "[]"

            # Strip markdown fences if Gemini adds them despite instructions
            raw = raw.replace("```json", "").replace("```", "").strip()

            results = json.loads(raw)
            logger.info(f"Gemini arbitrated {len(results)} conflicts")
            return results

        except json.JSONDecodeError as e:
            logger.error(f"Gemini arbiter returned invalid JSON: {e}")
            # Fall back: return empty so consensus keeps Google's reading
            return []
        except Exception as e:
            logger.error(f"Gemini arbitration failed: {e}")
            return []
