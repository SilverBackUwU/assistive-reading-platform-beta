from __future__ import annotations

import re

from core.config import Settings
from schemas.braille import BrailleRequest, BrailleResponse
from services.braille.brf_formatter import format_brf

try:
    import louis  # type: ignore
except ImportError:  # pragma: no cover
    louis = None


class LiblouisBrailleService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def transcribe(self, request: BrailleRequest) -> BrailleResponse:
        if louis is not None:
            table = request.table or self._settings.liblouis_table
            braille_unicode = louis.translateString([table], request.text, mode=0)
            return BrailleResponse(
                source_text=request.text,
                braille_unicode=braille_unicode,
                brf_text=format_brf(
                    text=braille_unicode,
                    line_width=self._settings.brf_line_width,
                    page_height=self._settings.brf_page_height,
                ),
                table=table,
                engine="liblouis",
            )

        braille_unicode = _fallback_grade2_braille(request.text)
        return BrailleResponse(
            source_text=request.text,
            braille_unicode=braille_unicode,
            brf_text=format_brf(
                text=braille_unicode,
                line_width=self._settings.brf_line_width,
                page_height=self._settings.brf_page_height,
            ),
            table="fallback-en-us-g2",
            engine="portable-fallback",
        )


_WORD_CONTRACTIONS: dict[str, str] = {
    "and": "⠯",
    "for": "⠿",
    "of": "⠷",
    "the": "⠮",
    "with": "⠾",
}

_PART_CONTRACTIONS: list[tuple[str, str]] = [
    ("ch", "⠡"),
    ("sh", "⠩"),
    ("th", "⠹"),
    ("wh", "⠱"),
    ("gh", "⠣"),
    ("ed", "⠫"),
    ("er", "⠻"),
    ("ou", "⠳"),
    ("ow", "⠪"),
    ("st", "⠌"),
    ("ar", "⠜"),
    ("ing", "⠬"),
]

_LETTER_MAP: dict[str, str] = {
    "a": "⠁",
    "b": "⠃",
    "c": "⠉",
    "d": "⠙",
    "e": "⠑",
    "f": "⠋",
    "g": "⠛",
    "h": "⠓",
    "i": "⠊",
    "j": "⠚",
    "k": "⠅",
    "l": "⠇",
    "m": "⠍",
    "n": "⠝",
    "o": "⠕",
    "p": "⠏",
    "q": "⠟",
    "r": "⠗",
    "s": "⠎",
    "t": "⠞",
    "u": "⠥",
    "v": "⠧",
    "w": "⠺",
    "x": "⠭",
    "y": "⠽",
    "z": "⠵",
}

_DIGIT_MAP: dict[str, str] = {
    "1": "⠁",
    "2": "⠃",
    "3": "⠉",
    "4": "⠙",
    "5": "⠑",
    "6": "⠋",
    "7": "⠛",
    "8": "⠓",
    "9": "⠊",
    "0": "⠚",
}

_NUMBER_PREFIX = "⠼"
_CAPITAL_PREFIX = "⠠"


def _fallback_grade2_braille(text: str) -> str:
    parts = re.findall(r"\w+|[^\w\s]|\s+", text, flags=re.UNICODE)
    output: list[str] = []

    for part in parts:
        if part.isspace():
            output.append(part)
            continue

        if part.isalpha():
            output.append(_translate_word(part))
            continue

        if part.isdigit():
            output.append(_translate_number(part))
            continue

        output.append(part)

    return "".join(output)


def _translate_word(word: str) -> str:
    lower = word.lower()
    if lower in _WORD_CONTRACTIONS:
        return _apply_caps(word, _WORD_CONTRACTIONS[lower])

    result: list[str] = []
    index = 0
    while index < len(word):
        chunk = None
        for pattern, braille in _PART_CONTRACTIONS:
            if lower.startswith(pattern, index):
                chunk = braille
                index += len(pattern)
                break
        if chunk is not None:
            result.append(chunk)
            continue

        ch = word[index]
        if ch.isupper():
            result.append(_CAPITAL_PREFIX)
            result.append(_LETTER_MAP.get(ch.lower(), ch))
        else:
            result.append(_LETTER_MAP.get(ch, ch))
        index += 1

    return "".join(result)


def _translate_number(value: str) -> str:
    return _NUMBER_PREFIX + "".join(_DIGIT_MAP.get(ch, ch) for ch in value)


def _apply_caps(original: str, braille: str) -> str:
    if original.isupper():
        return _CAPITAL_PREFIX + braille
    if original[:1].isupper():
        return _CAPITAL_PREFIX + braille
    return braille
