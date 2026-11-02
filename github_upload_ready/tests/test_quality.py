"""Tests for blur and resolution checks."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.quality import analyze_blur, analyze_resolution


def test_sharp_not_blurry(sharp_image: np.ndarray) -> None:
    result = analyze_blur(sharp_image, CaptureTrustConfig())
    assert result["is_blurry"] is False
    assert result["severity"] in ("none", "low")


def test_blurry_detected(blurry_image: np.ndarray) -> None:
    result = analyze_blur(blurry_image, CaptureTrustConfig())
    assert result["is_blurry"] is True
    assert result["severity"] in ("medium", "high")


def test_blur_signals_present(sharp_image: np.ndarray) -> None:
    result = analyze_blur(sharp_image, CaptureTrustConfig())
    for key in ("laplacian_variance", "tenengrad_score", "center_edge_density"):
        assert key in result


def test_low_resolution_flagged(low_resolution_image: np.ndarray) -> None:
    result = analyze_resolution(low_resolution_image, CaptureTrustConfig())
    assert result["is_low_resolution"] is True
    assert result["severity"] in ("low", "medium", "high")


def test_adequate_resolution_passes(sharp_image: np.ndarray) -> None:
    result = analyze_resolution(sharp_image, CaptureTrustConfig())
    assert result["is_low_resolution"] is False
    assert result["severity"] == "none"


def test_aspect_ratio_label(sharp_image: np.ndarray) -> None:
    result = analyze_resolution(sharp_image, CaptureTrustConfig())
    assert isinstance(result["aspect_ratio_label"], str)
    assert result["aspect_ratio"] > 0


def test_blur_severity_scales_with_resolution() -> None:
    # A large, mildly-soft image and a small one of the same content should be
    # judged consistently because blur is measured at a common working size.
    import cv2

    rng = np.random.default_rng(1)
    big = np.full((3000, 4000, 3), 130, dtype=np.uint8)
    cv2.circle(big, (2000, 1500), 700, (90, 160, 210), -1)
    cv2.putText(big, "TEXT", (900, 2400), cv2.FONT_HERSHEY_SIMPLEX, 12, (10, 10, 10), 24)
    big = cv2.add(big, rng.integers(0, 6, big.shape, dtype=np.int16).astype(np.uint8))
    result = analyze_blur(big, CaptureTrustConfig())
    # Should not collapse to "high" purely because the image is large.
    assert result["severity"] in ("none", "low", "medium")
    assert "sharpness_score" in result


def test_directionality_reported() -> None:
    import numpy as np

    rng = np.random.default_rng(3)
    img = rng.integers(0, 256, (700, 900, 3), dtype=np.uint8)
    result = analyze_blur(img, CaptureTrustConfig())
    assert "directionality" in result
    assert 0.0 <= result["directionality"] <= 1.0


def test_reject_blurry_policy() -> None:
    # A medium/high blur image must not be acceptable even if the score clears
    # the threshold, when reject_blurry is on (the default).
    import cv2
    import numpy as np

    base = np.random.default_rng(5).integers(0, 256, (900, 1200, 3), dtype=np.uint8)
    blurry = cv2.GaussianBlur(base, (0, 0), 8)
    from capturetrust import inspect_array

    r_on = inspect_array(blurry, config=CaptureTrustConfig(reject_blurry=True))
    if r_on.checks["blur"]["severity"] in ("medium", "high"):
        assert r_on.is_acceptable is False


def test_subject_detection_runs_without_crashing() -> None:
    import numpy as np

    from capturetrust.subject import detect_subject

    img = np.random.default_rng(9).integers(0, 256, (600, 800, 3), dtype=np.uint8)
    result = detect_subject(img, CaptureTrustConfig())
    assert "region" in result and "subject_type" in result
