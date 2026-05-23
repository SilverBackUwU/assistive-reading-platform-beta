"""
services/ocr/consensus.py
==========================
Consensus engine: merges 3 OCR outputs into one verified text.

Algorithm per token:
  1. If 2-of-3 agree  → accept (high confidence)
  2. If all 3 agree   → accept (highest confidence)
  3. If all 3 differ  → mark as conflict, route to Gemini arbiter
  4. After arbitration → replace conflict tokens with arbiter's choice

The merged text + per-word WordResult list is what goes to the API response.
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher

from schemas.ocr import LayerOutput, OCREngineLabel, WordResult

logger = logging.getLogger(__name__)


def merge(
    google:  LayerOutput,
    azure:   LayerOutput,
    gemini:  LayerOutput,
    arbiter_results: list[dict],   # from GeminiOCR.arbitrate()
) -> tuple[str, list[WordResult]]:
    """
    Merge three LayerOutputs into a single text string + word-level results.

    Returns:
        merged_text:  the final string shown in Stage 1 editor
        word_results: per-token metadata (confidence, source, conflict flag)
    """
    g_tokens = _tokenize(google.text)
    a_tokens = _tokenize(azure.text)
    m_tokens = _tokenize(gemini.text)

    # Align all three to the longest output using sequence matching
    max_len = max(len(g_tokens), len(a_tokens), len(m_tokens))
    g_tokens = _pad(g_tokens, max_len)
    a_tokens = _pad(a_tokens, max_len)
    m_tokens = _pad(m_tokens, max_len)

    # Build arbiter lookup: {index: {"chosen": str, "confidence": float}}
    arbiter_map: dict[int, dict] = {
        r["index"]: r for r in (arbiter_results or [])
        if "index" in r and "chosen" in r
    }

    word_results: list[WordResult] = []

    for i in range(max_len):
        g, a, m = g_tokens[i], a_tokens[i], m_tokens[i]

        # ── Case 1: arbitration result exists for this index ──────────────
        if i in arbiter_map:
            chosen = arbiter_map[i]["chosen"]
            confidence = arbiter_map[i].get("confidence", 0.75)
            word_results.append(WordResult(
                text=chosen,
                confidence=confidence,
                source=OCREngineLabel.GEMINI,
                conflict=False,          # resolved by arbiter
                alternatives=[g, a, m],
            ))
            continue

        # ── Case 2: all three agree ────────────────────────────────────────
        if g == a == m:
            word_results.append(WordResult(
                text=g,
                confidence=0.97,
                source=OCREngineLabel.CONSENSUS,
                conflict=False,
            ))
            continue

        # ── Case 3: 2-of-3 majority ───────────────────────────────────────
        majority = _majority_vote(g, a, m)
        if majority is not None:
            # Identify which engine was the odd one out
            source = _majority_source(g, a, m, majority)
            word_results.append(WordResult(
                text=majority,
                confidence=0.88,
                source=source,
                conflict=False,
                alternatives=list({g, a, m} - {majority}),
            ))
            continue

        # ── Case 4: all three disagree → conflict ─────────────────────────
        # Use Google as the tentative text (highest accuracy on Sanskrit)
        # conflict=True → UI highlights this word in amber
        word_results.append(WordResult(
            text=g if g else (a if a else m),
            confidence=0.45,
            source=OCREngineLabel.CONFLICT,
            conflict=True,
            alternatives=[g, a, m],
        ))

    merged_text = " ".join(w.text for w in word_results if w.text.strip())
    conflict_count = sum(1 for w in word_results if w.conflict)

    logger.info(
        f"Consensus complete: {len(word_results)} tokens, "
        f"{conflict_count} conflicts"
    )
    return merged_text, word_results


def build_conflict_list(word_results: list[WordResult]) -> list[dict]:
    """
    Extracts conflict tokens for the Gemini arbiter.
    Returns format expected by GeminiOCR.arbitrate().
    """
    conflicts = []
    for i, w in enumerate(word_results):
        if w.conflict:
            conflicts.append({
                "index": i,
                "alternatives": w.alternatives,
            })
    return conflicts


def overall_confidence(word_results: list[WordResult]) -> float:
    """Average confidence across all resolved tokens."""
    if not word_results:
        return 0.0
    scores = [w.confidence for w in word_results]
    return round(sum(scores) / len(scores), 4)


# ── Private helpers ───────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """
    Split on whitespace. Preserves Devanagari punctuation (।, ॥) as tokens.
    Empty string → empty list.
    """
    if not text:
        return []
    return text.split()


def _pad(tokens: list[str], length: int) -> list[str]:
    """Right-pad with empty strings to reach target length."""
    return tokens + [""] * (length - len(tokens))


def _majority_vote(g: str, a: str, m: str) -> str | None:
    """Returns the word that appears at least twice, or None if all differ."""
    for word in (g, a, m):
        if [g, a, m].count(word) >= 2:
            return word
    return None


def _majority_source(g: str, a: str, m: str, majority: str) -> OCREngineLabel:
    """Identify which engine produced the majority reading."""
    if g == majority and a == majority:
        return OCREngineLabel.GOOGLE
    if g == majority and m == majority:
        return OCREngineLabel.GOOGLE
    if a == majority and m == majority:
        return OCREngineLabel.AZURE
    return OCREngineLabel.CONSENSUS
