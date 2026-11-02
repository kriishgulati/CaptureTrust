"""Tests for document detection and framing."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.document import analyze_document


def test_document_detected(document_image: np.ndarray) -> None:
    result = analyze_document(document_image, CaptureTrustConfig())
    assert result["document_detected"] is True
    assert result["document_area_ratio"] is not None
    assert 0.0 <= result["document_area_ratio"] <= 1.0


def test_no_document_returns_none_fields(sharp_image: np.ndarray) -> None:
    # A photo without a clean quadrilateral document.
    result = analyze_document(sharp_image, CaptureTrustConfig())
    if not result["document_detected"]:
        assert result["document_area_ratio"] is None
        assert result["severity"] == "none"


def test_flat_image_no_document(blank_image: np.ndarray) -> None:
    result = analyze_document(blank_image, CaptureTrustConfig())
    assert result["document_detected"] is False
    assert result["document_candidate_count"] == 0


def test_rotated_document_tilt(rotated_document_image: np.ndarray) -> None:
    result = analyze_document(rotated_document_image, CaptureTrustConfig())
    if result["document_detected"]:
        assert result["document_tilt_degrees"] is not None


def test_detector_robust_to_noise() -> None:
    rng = np.random.default_rng(2)
    noise = rng.integers(0, 255, (500, 700, 3), dtype=np.uint8)
    # Should not raise, regardless of whether a document is "found".
    result = analyze_document(noise, CaptureTrustConfig())
    assert "document_detected" in result
