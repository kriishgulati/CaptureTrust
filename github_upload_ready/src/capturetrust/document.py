"""Document detection and framing-quality estimation.

A lightweight, best-effort detector that looks for a dominant quadrilateral
resembling a document/card/receipt. It scores candidates on size, convexity
and aspect ratio rather than blindly taking the largest contour, then reports
framing quality (edge cropping, tilt and perspective distortion).

No document is *not* treated as an error: this library is also used for
ordinary photos.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import to_grayscale

__all__ = ["analyze_document"]


def _no_document() -> CheckResult:
    return {
        "document_detected": False,
        "document_candidate_count": 0,
        "document_area_ratio": None,
        "document_corners_visible": None,
        "document_edges_cut_off": None,
        "document_tilt_degrees": None,
        "perspective_distortion_score": None,
        "framing_score": None,
        "severity": "none",
    }


def analyze_document(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Detect a document-like quadrilateral and assess framing quality."""
    height, width = image.shape[:2]
    image_area = float(width * height)

    gray = to_grayscale(image)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    candidates = _find_quad_candidates(gray, image_area, config)
    if not candidates:
        result = _no_document()
        return result

    best_score, best_quad = max(candidates, key=lambda item: item[0])
    del best_score

    ordered = _order_corners(best_quad)
    area = cv2.contourArea(ordered.astype(np.float32))
    area_ratio = float(area / image_area)

    corners_visible, edges_cut_off = _corner_framing(ordered, width, height, config)
    tilt = _tilt_degrees(ordered)
    perspective = _perspective_distortion(ordered)
    framing = _framing_score(area_ratio, corners_visible, tilt, perspective)
    severity = _classify_framing(framing, edges_cut_off)

    return {
        "document_detected": True,
        "document_candidate_count": len(candidates),
        "document_area_ratio": round(area_ratio, 4),
        "document_corners_visible": bool(corners_visible),
        "document_edges_cut_off": bool(edges_cut_off),
        "document_tilt_degrees": round(tilt, 2),
        "perspective_distortion_score": round(perspective, 4),
        "framing_score": round(framing, 4),
        "severity": severity,
    }


def _find_quad_candidates(
    gray: np.ndarray, image_area: float, config: CaptureTrustConfig
) -> list[tuple[float, np.ndarray]]:
    """Return scored quadrilateral candidates ``(score, corners)``."""
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[float, np.ndarray]] = []
    min_area = config.document_min_area_ratio * image_area

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue

        quad = approx.reshape(4, 2).astype(np.float64)
        score = _score_candidate(quad, area, image_area)
        if score > 0:
            candidates.append((score, quad))

    return candidates


def _score_candidate(quad: np.ndarray, area: float, image_area: float) -> float:
    """Score a quad on relative size, rectangularity and aspect ratio."""
    ordered = _order_corners(quad)
    (tl, tr, br, bl) = ordered

    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)

    avg_w = (width_top + width_bottom) / 2.0
    avg_h = (height_left + height_right) / 2.0
    if avg_w <= 0 or avg_h <= 0:
        return 0.0

    aspect = max(avg_w, avg_h) / min(avg_w, avg_h)
    if aspect > 5.0:  # too elongated to be a document
        return 0.0

    area_ratio = area / image_area
    size_score = min(area_ratio / 0.5, 1.0)

    # Rectangularity: how close opposite sides are in length.
    width_balance = 1.0 - abs(width_top - width_bottom) / (avg_w + 1e-6)
    height_balance = 1.0 - abs(height_left - height_right) / (avg_h + 1e-6)
    rect_score = max(0.0, (width_balance + height_balance) / 2.0)

    aspect_score = 1.0 / aspect  # closer to 1.0 for near-square/standard shapes

    return float(0.5 * size_score + 0.35 * rect_score + 0.15 * aspect_score)


def _order_corners(points: np.ndarray) -> np.ndarray:
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = points.reshape(4, 2).astype(np.float64)
    ordered = np.zeros((4, 2), dtype=np.float64)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)
    ordered[0] = pts[np.argmin(s)]  # top-left
    ordered[2] = pts[np.argmax(s)]  # bottom-right
    ordered[1] = pts[np.argmin(diff)]  # top-right
    ordered[3] = pts[np.argmax(diff)]  # bottom-left
    return ordered


def _corner_framing(
    corners: np.ndarray, width: int, height: int, config: CaptureTrustConfig
) -> tuple[bool, bool]:
    """Return ``(all_corners_visible, edges_cut_off)``."""
    margin_x = config.document_edge_margin_ratio * width
    margin_y = config.document_edge_margin_ratio * height

    near_edge = False
    for x, y in corners:
        if (
            x <= margin_x
            or y <= margin_y
            or x >= width - 1 - margin_x
            or y >= height - 1 - margin_y
        ):
            near_edge = True
            break

    corners_visible = not near_edge
    return corners_visible, near_edge


def _tilt_degrees(corners: np.ndarray) -> float:
    """Estimate the tilt of the top edge from horizontal, in degrees."""
    tl, tr = corners[0], corners[1]
    angle = np.degrees(np.arctan2(tr[1] - tl[1], tr[0] - tl[0]))
    return float(abs(((angle + 45.0) % 90.0) - 45.0))


def _perspective_distortion(corners: np.ndarray) -> float:
    """Estimate perspective distortion from opposite-side length mismatch."""
    tl, tr, br, bl = corners
    width_top = np.linalg.norm(tr - tl)
    width_bottom = np.linalg.norm(br - bl)
    height_left = np.linalg.norm(bl - tl)
    height_right = np.linalg.norm(br - tr)

    w_mismatch = abs(width_top - width_bottom) / (max(width_top, width_bottom) + 1e-6)
    h_mismatch = abs(height_left - height_right) / (max(height_left, height_right) + 1e-6)
    return float(np.clip((w_mismatch + h_mismatch) / 2.0, 0.0, 1.0))


def _framing_score(
    area_ratio: float, corners_visible: bool, tilt: float, perspective: float
) -> float:
    """Blend framing signals into a 0..1 quality score (higher is better)."""
    score = 1.0
    if not corners_visible:
        score -= 0.35
    score -= min(tilt / 30.0, 1.0) * 0.25
    score -= perspective * 0.25
    if area_ratio < 0.2:
        score -= 0.15  # document occupies very little of the frame
    return float(np.clip(score, 0.0, 1.0))


def _classify_framing(framing: float, edges_cut_off: bool) -> Severity:
    if edges_cut_off and framing < 0.5:
        return "high"
    if framing < 0.55:
        return "medium"
    if framing < 0.8:
        return "low"
    return "none"


# Exposed for testing convenience.
_order_corners_public: object | None = _order_corners
