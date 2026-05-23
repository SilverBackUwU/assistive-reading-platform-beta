"""
services/ocr/preprocessor.py
=============================
Image preprocessing pipeline tuned for Devanagari manuscripts.
Runs on every upload before any OCR engine sees the image.

Also handles:
  - PDF → page 1 image conversion (requires poppler in PATH)
  - File size validation
  - MIME type detection
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Max dimensions — anything bigger than this is an unreasonable scan
MAX_WIDTH = 6000
MAX_HEIGHT = 8000

# Target DPI equivalent after upscale
MIN_EFFECTIVE_WIDTH = 2000  # below this → upscale 2x


def preprocess(image_bytes: bytes) -> bytes:
    """
    Full preprocessing pipeline.
    Input:  raw bytes from upload (PNG, JPG, TIFF, WEBP)
    Output: cleaned PNG bytes ready for all three OCR engines
    """
    img = _bytes_to_cv2(image_bytes)
    img = _resize_if_needed(img)
    gray = _to_grayscale(img)
    deskewed = _deskew(gray)
    denoised = _denoise(deskewed)
    binary = _binarize(denoised)
    upscaled = _upscale_if_needed(binary)
    return _cv2_to_png_bytes(upscaled)


def pdf_to_image_bytes(pdf_bytes: bytes) -> bytes:
    """
    Convert page 1 of a PDF to preprocessed PNG bytes.
    Requires: poppler installed and in system PATH.

    Windows install:
      1. Download from https://github.com/oschwartz10612/poppler-windows/releases
      2. Extract to C:\\poppler\\
      3. Add C:\\poppler\\bin to Windows PATH
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise RuntimeError(
            "pdf2image not installed. Run: pip install pdf2image\n"
            "Also install poppler: see services/ocr/preprocessor.py docstring"
        )

    logger.info("Converting PDF page 1 → image")
    pages = convert_from_bytes(
        pdf_bytes,
        first_page=1,
        last_page=1,    # MVP: page 1 only
        dpi=300,        # 300 DPI is minimum for reliable Devanagari OCR
        fmt="PNG",
    )

    if not pages:
        raise ValueError(
            "PDF appears to have no pages or could not be rendered")

    # PIL Image → bytes
    buf = io.BytesIO()
    pages[0].save(buf, format="PNG")
    return preprocess(buf.getvalue())


def validate_file(
    content: bytes,
    filename: str,
    max_image_bytes: int,
    max_pdf_bytes: int,
) -> str:
    """
    Validates file type and size.
    Returns: 'image' or 'pdf'
    Raises:  ValueError with a user-facing message on any failure
    """
    ext = Path(filename).suffix.lower()
    allowed_image = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".webp"}
    allowed_pdf = {".pdf"}

    if ext in allowed_image:
        if len(content) > max_image_bytes:
            raise ValueError(
                f"Image exceeds maximum size of "
                f"{max_image_bytes // (1024*1024)} MB"
            )
        return "image"

    if ext in allowed_pdf:
        if len(content) > max_pdf_bytes:
            raise ValueError(
                f"PDF exceeds maximum size of "
                f"{max_pdf_bytes // (1024*1024)} MB"
            )
        return "pdf"

    raise ValueError(
        f"Unsupported file type '{ext}'. "
        f"Allowed: {', '.join(sorted(allowed_image | allowed_pdf))}"
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(
            "Could not decode image. File may be corrupted or unsupported format."
        )
    return img


def _resize_if_needed(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if w > MAX_WIDTH or h > MAX_HEIGHT:
        scale = min(MAX_WIDTH / w, MAX_HEIGHT / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug(f"Resized {w}×{h} → {new_w}×{new_h}")
    return img


def _to_grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Corrects rotation. Critical for Shirorekha (header line) alignment.
    Skewed images break conjunct detection in every engine.
    """
    try:
        coords = np.column_stack(np.where(gray < 200))
        if len(coords) < 10:
            return gray  # not enough dark pixels to estimate angle
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        # Only correct if skew is meaningful (> 0.5 degrees)
        if abs(angle) < 0.5:
            return gray
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        deskewed = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        logger.debug(f"Deskewed by {angle:.2f}°")
        return deskewed
    except Exception as e:
        logger.warning(f"Deskew failed, using original: {e}")
        return gray


def _denoise(gray: np.ndarray) -> np.ndarray:
    """
    Removes salt-and-pepper noise while preserving Shirorekha thickness.
    Uses a small kernel to avoid destroying thin conjunct strokes.
    """
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def _binarize(gray: np.ndarray) -> np.ndarray:
    """
    Adaptive thresholding handles uneven lighting in manuscript scans.
    Block size 31 is tuned for Devanagari glyph sizes at 300 DPI.
    """
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,   # block size — must be odd
        10,   # constant subtracted from mean
    )


def _upscale_if_needed(binary: np.ndarray) -> np.ndarray:
    """
    Upscale if image is too small. Low-DPI scans miss conjunct details.
    """
    h, w = binary.shape
    if w < MIN_EFFECTIVE_WIDTH:
        scale = MIN_EFFECTIVE_WIDTH / w
        new_w, new_h = int(w * scale), int(h * scale)
        binary = cv2.resize(binary, (new_w, new_h),
                            interpolation=cv2.INTER_CUBIC)
        logger.debug(f"Upscaled {w}×{h} → {new_w}×{new_h}")
    return binary


def _cv2_to_png_bytes(img: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("Failed to encode preprocessed image as PNG")
    return encoded.tobytes()
