"""Best-effort detection of the main subject (a face or a document).

The goal is modest and safe: when we can confidently locate the subject, the
quality checks can focus on it (a blurry face in front of a sharp background
should be judged on the face). When we cannot, we return ``None`` and callers
fall back to their default whole-frame or centre-region behaviour, so subject
detection can only help or be neutral - never make a check worse.

Regions are returned as fractions of the image (x, y, w, h in 0..1) so they are
independent of resolution.
"""

from __future__ import annotations

import os

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage
from .utils import to_grayscale

Region = tuple[float, float, float, float]  # (x, y, w, h) as fractions

_FACE_CASCADES: list[cv2.CascadeClassifier] | None = None


def _face_cascades() -> list[cv2.CascadeClassifier]:
    global _FACE_CASCADES
    if _FACE_CASCADES is None:
        base = cv2.data.haarcascades  # type: ignore[attr-defined]
        names = ["haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml"]
        loaded = []
        for name in names:
            path = os.path.join(base, name)
            classifier = cv2.CascadeClassifier(path)
            if not classifier.empty():
                loaded.append(classifier)
        _FACE_CASCADES = loaded
    return _FACE_CASCADES


def detect_subject(image: BGRImage, config: CaptureTrustConfig) -> dict[str, object]:
    """Locate the main subject, returning its region and type.

    Returns a dict with ``region`` (fractions or ``None``) and ``subject_type``
    (``"face"``, ``"document"`` or ``None``).
    """
    gray = to_grayscale(image)
    height, width = gray.shape

    face = _detect_face(gray, width, height)
    if face is not None:
        return {"region": face, "subject_type": "face"}

    document = _detect_document_region(gray, width, height)
    if document is not None:
        return {"region": document, "subject_type": "document"}

    return {"region": None, "subject_type": None}


def _detect_face(gray: np.ndarray, width: int, height: int) -> Region | None:
    frame_area = float(width * height)
    candidates: list[tuple[int, int, int, int]] = []
    for cascade in _face_cascades():
        for scale_factor, min_neighbors, min_size in ((1.1, 4, 40), (1.05, 3, 30)):
            found = cascade.detectMultiScale(
                gray,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                minSize=(min_size, min_size),
            )
            for box in found:
                candidates.append((int(box[0]), int(box[1]), int(box[2]), int(box[3])))

    if not candidates:
        return None

    # Keep the largest plausible face: not a speck, not essentially the frame.
    best = max(candidates, key=lambda b: b[2] * b[3])
    x, y, w, h = best
    area_ratio = (w * h) / frame_area
    if area_ratio < 0.02 or area_ratio > 0.9:
        return None

    # Expand slightly so the whole face (not just the inner box) is covered.
    pad_w, pad_h = 0.15 * w, 0.15 * h
    fx = max(0.0, (x - pad_w) / width)
    fy = max(0.0, (y - pad_h) / height)
    fw = min(1.0 - fx, (w + 2 * pad_w) / width)
    fh = min(1.0 - fy, (h + 2 * pad_h) / height)
    return (fx, fy, fw, fh)


def _detect_document_region(gray: np.ndarray, width: int, height: int) -> Region | None:
    """Find a large document-like quadrilateral and return its bounding box."""
    frame_area = float(width * height)
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    best_ratio = 0.0
    best_box: tuple[int, int, int, int] | None = None
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 0.12 * frame_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4:
            continue
        ratio = area / frame_area
        if ratio > best_ratio:
            best_ratio = ratio
            rect = cv2.boundingRect(approx)
            best_box = (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))

    if best_box is None:
        return None

    x, y, w, h = best_box
    return (x / width, y / height, w / width, h / height)
