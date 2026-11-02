"""Experimental screen-recapture risk heuristic.

**This module is experimental.** It combines several weak visual indicators
that are *sometimes* associated with photographs of screens (moire patterns,
regular pixel-grid frequency peaks, strong directional line texture). It never
concludes that an image is "fake" or "fraudulent" - only that some visual
characteristics are, or are not, consistent with a screen recapture.

Fabrics, printed halftone pages, brick walls, window blinds and heavy JPEG
compression can all produce similar signals, so false positives are expected.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import CaptureTrustConfig
from .types import BGRImage, CheckResult, Severity
from .utils import to_grayscale

__all__ = ["analyze_recapture"]

_WARNING = "Experimental visual heuristic only; not proof of recapture or fraud."


def analyze_recapture(image: BGRImage, config: CaptureTrustConfig) -> CheckResult:
    """Estimate a screen-recapture risk score in ``[0, 1]``."""
    gray = to_grayscale(image).astype(np.float32)

    # Work on a bounded size so the FFT cost stays predictable.
    gray = _resize_max(gray, 512)

    # Near-flat images carry no meaningful frequency structure. Dividing by an
    # effectively-zero spectral mean would otherwise amplify floating-point
    # rounding into spurious "peaks", so short-circuit to a low-risk result.
    if float(np.std(gray)) < 1.0:
        return {
            "screen_recapture_score": 0.0,
            "screen_recapture_risk": "low",
            "frequency_peak_score": 0.0,
            "line_pattern_score": 0.0,
            "moire_score": 0.0,
            "reflection_signal_score": round(_reflection_score(image), 4),
            "severity": "none",
            "warning": _WARNING,
        }

    frequency_peak_score, moire_score = _spectral_scores(gray)
    line_pattern_score = _line_pattern_score(gray)
    reflection_signal_score = _reflection_score(image)

    combined = float(
        0.20 * frequency_peak_score
        + 0.50 * moire_score
        + 0.20 * line_pattern_score
        + 0.10 * reflection_signal_score
    )

    # Moire (mid-frequency beating between a display's pixel grid and the camera
    # sensor) is the one signal that genuinely distinguishes a photographed
    # screen from an ordinary photo. Frequency peaks and directional line
    # texture fire on all sorts of normal images (faces, edges, backgrounds),
    # so without meaningful moire energy the combined score is strongly damped.
    # This heavily favours avoiding false positives, which is the right default
    # for an experimental, non-accusatory signal.
    if moire_score < 0.20:
        combined *= 0.4

    combined = float(np.clip(combined, 0.0, 1.0))

    risk = _classify_risk(combined, config)
    severity: Severity = "none" if risk == "low" else risk  # type: ignore[assignment]

    return {
        "screen_recapture_score": round(combined, 4),
        "screen_recapture_risk": risk,
        "frequency_peak_score": round(frequency_peak_score, 4),
        "line_pattern_score": round(line_pattern_score, 4),
        "moire_score": round(moire_score, 4),
        "reflection_signal_score": round(reflection_signal_score, 4),
        "severity": severity,
        "warning": _WARNING,
    }


def _resize_max(gray: np.ndarray, max_dim: int) -> np.ndarray:
    h, w = gray.shape[:2]
    scale = max_dim / float(max(h, w))
    if scale < 1.0:
        return cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return gray


def _spectral_scores(gray: np.ndarray) -> tuple[float, float]:
    """Return ``(frequency_peak_score, moire_score)`` from the FFT magnitude."""
    normalised = gray - float(np.mean(gray))
    window = np.outer(np.hanning(gray.shape[0]), np.hanning(gray.shape[1]))
    spectrum = np.fft.fftshift(np.fft.fft2(normalised * window))
    magnitude = np.abs(spectrum)

    cy, cx = np.array(magnitude.shape) // 2
    # Suppress the DC component and its immediate neighbourhood.
    magnitude[cy - 2 : cy + 3, cx - 2 : cx + 3] = 0.0

    mean_mag = float(np.mean(magnitude)) + 1e-6
    peak_mag = float(np.max(magnitude))
    peak_ratio = peak_mag / mean_mag

    # Regular screen grids produce sharp isolated peaks -> high peak ratio.
    frequency_peak_score = float(np.clip((peak_ratio - 40.0) / 260.0, 0.0, 1.0))

    # Moire energy: fraction of spectral energy in a mid-frequency annulus.
    yy, xx = np.ogrid[: magnitude.shape[0], : magnitude.shape[1]]
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    max_radius = float(radius.max()) + 1e-6
    mid = (radius > 0.25 * max_radius) & (radius < 0.6 * max_radius)
    total_energy = float(np.sum(magnitude)) + 1e-6
    mid_energy = float(np.sum(magnitude[mid]))
    moire_score = float(np.clip((mid_energy / total_energy - 0.25) / 0.35, 0.0, 1.0))

    return frequency_peak_score, moire_score


def _line_pattern_score(gray: np.ndarray) -> float:
    """Score periodic horizontal/vertical structure via projection variance."""
    g = gray - float(np.mean(gray))
    col_profile = np.mean(np.abs(np.diff(g, axis=1)), axis=0)
    row_profile = np.mean(np.abs(np.diff(g, axis=0)), axis=1)

    def periodicity(profile: np.ndarray) -> float:
        profile = profile - float(np.mean(profile))
        if profile.size < 8 or float(np.std(profile)) < 1e-6:
            return 0.0
        spectrum = np.abs(np.fft.rfft(profile))
        spectrum[0] = 0.0
        peak = float(np.max(spectrum))
        mean = float(np.mean(spectrum)) + 1e-6
        return float(np.clip((peak / mean - 6.0) / 24.0, 0.0, 1.0))

    return max(periodicity(col_profile), periodicity(row_profile))


def _reflection_score(image: BGRImage) -> float:
    """Rough proxy for large, smooth bright reflection patches."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    bright = (value > 210).astype(np.uint8)
    bright_ratio = float(np.count_nonzero(bright)) / float(bright.size)
    return float(np.clip((bright_ratio - 0.02) / 0.2, 0.0, 1.0))


def _classify_risk(score: float, config: CaptureTrustConfig) -> str:
    if score >= config.screen_recapture_high_threshold:
        return "high"
    if score >= config.screen_recapture_medium_threshold:
        return "medium"
    return "low"
