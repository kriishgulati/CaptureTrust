"""Blur detection and resolution/aspect-ratio checks.

Both checks live here because they operate on the most basic image
properties and are almost always evaluated together.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import downscale_longest_side, to_grayscale

__all__ = ["analyze_blur", "analyze_resolution"]


def analyze_blur(
    image: BGRImage,
    config: CaptureTrustConfig,
    region: tuple[float, float, float, float] | None = None,
) -> CheckResult:
    """Estimate image sharpness, focused on the subject where possible.

    Sharpness is measured at a normalised working resolution so the numbers are
    comparable across camera resolutions. If ``region`` (a subject bounding box
    in fractions) is supplied - typically a detected face or document - the
    measurement is taken there, because that is what actually matters. Without
    it, the decision is weighted toward the centre of the frame, which is a good
    default guess for where the subject sits but is fooled by busy backgrounds.
    """
    work = downscale_longest_side(image, config.working_resolution)
    gray = to_grayscale(work)

    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    tenengrad_score = _tenengrad(gray)

    height, width = gray.shape
    if region is not None:
        rx, ry, rw, rh = region
        cx0, cy0 = int(rx * width), int(ry * height)
        cx1, cy1 = int((rx + rw) * width), int((ry + rh) * height)
    else:
        cy0, cy1 = int(height * 0.22), int(height * 0.85)
        cx0, cx1 = int(width * 0.25), int(width * 0.75)
    cx0, cy0 = max(0, cx0), max(0, cy0)
    cx1 = min(width, max(cx1, cx0 + 1))
    cy1 = min(height, max(cy1, cy0 + 1))
    center = np.ascontiguousarray(gray[cy0:cy1, cx0:cx1])
    center_laplacian = float(cv2.Laplacian(center, cv2.CV_64F).var())
    center_edge_density = _edge_density(center)
    directionality = _directionality(center)
    edge_crispness = _edge_crispness(center)

    severity = _classify_blur(
        center_laplacian, center_edge_density, laplacian_variance, config.blur_threshold
    )
    bump: dict[Severity, Severity] = {"none": "low", "low": "medium", "medium": "high"}
    # Motion blur is directional: its gradient energy is concentrated along one
    # axis (streaks), whereas genuine detail has edges in all directions.
    if directionality >= 0.45 and severity != "high":
        severity = bump[severity]
    # Soft edges are a blur signature even amid heavy texture (motion-blurred
    # grass keeps a high Laplacian variance but its edges are soft). The floor
    # scales with the sharp boundary, so the lenient "photos" preset does not
    # penalise genuinely sharp but smooth or bokeh subjects.
    if edge_crispness < 0.54 * config.blur_threshold and severity != "high":
        severity = bump[severity]
    is_blurry = severity in ("medium", "high")

    return {
        "blur_score": round(laplacian_variance, 3),
        "laplacian_variance": round(laplacian_variance, 3),
        "center_laplacian_variance": round(center_laplacian, 3),
        "center_edge_density": round(center_edge_density, 4),
        "directionality": round(directionality, 3),
        "edge_crispness": round(edge_crispness, 2),
        "tenengrad_score": round(tenengrad_score, 3),
        "sharpness_score": round(center_laplacian, 3),
        "is_blurry": is_blurry,
        "severity": severity,
    }


def _tenengrad(gray: np.ndarray) -> float:
    """Tenengrad focus measure: mean squared Sobel gradient magnitude."""
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = gx * gx + gy * gy
    return float(np.mean(magnitude) / 1000.0)


def _edge_density(gray: np.ndarray) -> float:
    """Fraction of pixels classified as edges by the Canny detector."""
    edges = cv2.Canny(gray, 50, 150)
    return float(np.count_nonzero(edges)) / float(edges.size)


def _edge_crispness(gray: np.ndarray) -> float:
    """Peak gradient magnitude (99th percentile): how sharp the edges are.

    Blur softens edges, lowering the peak gradient even when a textured image
    still has many edges. Genuine sharp detail produces a high peak.
    """
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return float(np.percentile(np.sqrt(gx * gx + gy * gy), 99))


def _directionality(gray: np.ndarray) -> float:
    """Gradient directionality (structure-tensor coherence), in [0, 1].

    Close to 0 means gradient energy is spread across all orientations (genuine
    detail); close to 1 means it is concentrated along one axis, the signature
    of motion blur. Computed from the eigenvalues of the averaged structure
    tensor of the image gradients.
    """
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    jxx = float(np.mean(gx * gx))
    jyy = float(np.mean(gy * gy))
    jxy = float(np.mean(gx * gy))
    trace = jxx + jyy
    discriminant = max(trace * trace / 4.0 - (jxx * jyy - jxy * jxy), 0.0) ** 0.5
    lambda1 = trace / 2.0 + discriminant
    lambda2 = trace / 2.0 - discriminant
    return float((lambda1 - lambda2) / (lambda1 + lambda2 + 1e-9))


def _classify_blur(
    center_laplacian: float,
    center_edge_density: float,
    global_laplacian: float,
    threshold: float,
) -> Severity:
    """Grade blur from the centre-region Laplacian variance.

    Calibration against a labelled set of real photographs showed the
    centre-region Laplacian variance to be the single most reliable separator
    of sharp from blurry images, so severity is graded proportionally against
    the configured sharp boundary. Edge density and whole-frame variance are
    still reported for transparency but are not used for the decision, because
    textured blur (motion-blurred grass, foliage) can inflate them. Bands are
    provisional; see docs/limitations.
    """
    if center_laplacian >= threshold:
        return "none"
    if center_laplacian >= 0.55 * threshold:
        return "low"
    if center_laplacian >= 0.20 * threshold:
        return "medium"
    return "high"


def analyze_resolution(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Check image dimensions, megapixels and aspect ratio."""
    height, width = image.shape[:2]
    megapixels = (width * height) / 1_000_000.0

    below_min = width < config.min_width or height < config.min_height
    very_small = (width * height) < (320 * 240)

    if very_small:
        severity: Severity = "high"
    elif below_min:
        severity = "low"
    else:
        severity = "none"

    aspect_ratio = width / height if height else 0.0
    aspect_label, unusual = _aspect_label(aspect_ratio)

    return {
        "width": int(width),
        "height": int(height),
        "megapixels": round(megapixels, 3),
        "is_low_resolution": bool(below_min or very_small),
        "aspect_ratio": round(aspect_ratio, 3),
        "aspect_ratio_label": aspect_label,
        "unusual_aspect_ratio": bool(unusual),
        "severity": severity,
    }


def _aspect_label(ratio: float) -> tuple[str, bool]:
    """Classify an aspect ratio and flag extreme values."""
    if ratio <= 0:
        return "unknown", True
    normalised = ratio if ratio >= 1.0 else 1.0 / ratio
    known = {
        "square": 1.0,
        "standard": 4 / 3,
        "photo": 3 / 2,
        "widescreen": 16 / 9,
    }
    best_label = min(known, key=lambda k: abs(known[k] - normalised))
    within_tolerance = abs(known[best_label] - normalised) <= 0.12
    if not within_tolerance:
        unusual = normalised > 2.4
        return ("panoramic" if unusual else "nonstandard"), unusual
    return best_label, False
