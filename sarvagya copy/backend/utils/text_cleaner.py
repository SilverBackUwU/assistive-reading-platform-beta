from __future__ import annotations

import re


_DATA_IMAGE_RE = re.compile(
    r"data\s*\\?:\s*image/[a-z0-9.+-]+;base64\s*,\s*[a-z0-9+/=\s\\]+",
    re.IGNORECASE | re.DOTALL,
)
_MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]]*]\(\s*data\s*\\?:\s*image/[a-z0-9.+-]+;base64\s*,.*?\)",
    re.IGNORECASE | re.DOTALL,
)
_HTML_IMAGE_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*['\"]?\s*data\s*\\?:\s*image/[^>]+>",
    re.IGNORECASE | re.DOTALL,
)
_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\s*|\s*```", re.DOTALL)
_GIANT_BASE64_RE = re.compile(r"(?<![\w+/=])(?:[A-Za-z0-9+/]{80,}={0,2})(?![\w+/=])")
_BASE64_BLOCK_RE = re.compile(r"(?:^[A-Za-z0-9+/=]{60,}\s*$\n?){2,}", re.MULTILINE | re.DOTALL)
_LONG_TOKEN_RE = re.compile(r"\S{1200,}", re.DOTALL)
_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")

_MAX_CLEAN_TEXT_CHARS = 200_000
_MAX_SINGLE_TOKEN_CHARS = 1_200
_BASE64_LINE_RE = re.compile(r"^[A-Za-z0-9+/=\s]{80,}$")


def clean_ocr_text(text: str | None) -> str:
    """
    Strip transport artifacts and model mistakes from OCR text.

    Returns an empty string when the response is mostly encoded garbage rather
    than human-readable OCR output.
    """
    if not text:
        return ""

    value = str(text).replace("\r\n", "\n").replace("\r", "\n")

    if _looks_like_garbage(value):
        return ""

    value = _MARKDOWN_IMAGE_RE.sub("", value)
    value = _HTML_IMAGE_RE.sub("", value)
    value = _DATA_IMAGE_RE.sub("", value)
    value = _FENCE_RE.sub("", value)
    value = _BASE64_BLOCK_RE.sub("", value)
    value = _GIANT_BASE64_RE.sub("", value)
    value = _LONG_TOKEN_RE.sub("", value)

    value = "\n".join(_WHITESPACE_RE.sub(" ", line).strip() for line in value.split("\n"))
    value = _BLANK_LINES_RE.sub("\n\n", value).strip()

    if not value or _looks_like_garbage(value):
        return ""

    return value


def is_valid_ocr_text(text: str | None) -> bool:
    if not text or not str(text).strip():
        return False

    value = str(text)
    if contains_encoded_image_payload(value):
        return False
    if contains_giant_encoded_string(value) or _looks_like_garbage(value):
        return False
    if _LONG_TOKEN_RE.search(value):
        return False

    return bool(clean_ocr_text(value).strip())


def contains_encoded_image_payload(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"data\s*\\?:\s*image", str(text), flags=re.IGNORECASE))


def contains_giant_encoded_string(text: str | None) -> bool:
    if not text:
        return False
    value = str(text)
    if _LONG_TOKEN_RE.search(value) or _BASE64_BLOCK_RE.search(value):
        return True
    return bool(_GIANT_BASE64_RE.search(value))


def preview_ocr_text(text: str | None, limit: int = 240) -> str:
    if not text:
        return ""

    value = str(text).replace("\r", "\\r").replace("\n", "\\n")
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _looks_like_garbage(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True

    if len(stripped) > _MAX_CLEAN_TEXT_CHARS:
        return True

    if re.search(r"data\s*\\?:\s*image", stripped, flags=re.IGNORECASE):
        non_data_text = _DATA_IMAGE_RE.sub("", stripped)
        if len(non_data_text.strip()) < 20:
            return True

    tokens = re.findall(r"\S+", stripped)
    if any(len(token) > _MAX_SINGLE_TOKEN_CHARS for token in tokens):
        return True

    base64_line_chars = 0
    nonempty_lines = [line.strip() for line in stripped.split("\n") if line.strip()]
    for line in nonempty_lines:
        if _BASE64_LINE_RE.match(line):
            base64_line_chars += len(re.sub(r"\s+", "", line))

    if base64_line_chars > 2_000:
        readable_chars = len(re.findall(r"[\w\u0900-\u097F]", stripped, flags=re.UNICODE))
        if base64_line_chars / max(readable_chars, 1) > 0.60:
            return True

    return False
