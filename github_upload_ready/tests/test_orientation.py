"""Tests for orientation estimation."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.orientation import analyze_orientation


def test_returns_expected_keys(document_image: np.ndarray) -> None:
    result = analyze_orientation(document_image, CaptureTrustConfig())
    for key in ("estimated_rotation_degrees", "is_rotated", "severity"):
        assert key in result


def test_axis_aligned_low_rotation(document_image: np.ndarray) -> None:
    result = analyze_orientation(document_image, CaptureTrustConfig())
    rot = result["estimated_rotation_degrees"]
    if rot is not None:
        assert abs(rot) < 5.0


def test_flat_image_no_lines(blank_image: np.ndarray) -> None:
    result = analyze_orientation(blank_image, CaptureTrustConfig())
    assert result["severity"] == "none"
