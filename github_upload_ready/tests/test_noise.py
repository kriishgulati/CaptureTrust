"""Tests for noise estimation."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.noise import analyze_noise


def test_flat_image_low_noise(blank_image: np.ndarray) -> None:
    result = analyze_noise(blank_image, CaptureTrustConfig())
    assert result["severity"] == "none"
    assert result["is_noisy"] is False


def test_noisy_image_detected() -> None:
    rng = np.random.default_rng(1)
    noisy = rng.integers(0, 255, (600, 800, 3), dtype=np.uint8)
    result = analyze_noise(noisy, CaptureTrustConfig())
    assert 0.0 <= result["noise_score"] <= 1.0
    assert result["severity"] in ("low", "medium", "high")


def test_score_bounded(blank_image: np.ndarray) -> None:
    result = analyze_noise(blank_image, CaptureTrustConfig())
    assert 0.0 <= result["noise_score"] <= 1.0
