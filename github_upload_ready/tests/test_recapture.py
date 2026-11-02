"""Tests for the experimental screen-recapture heuristic."""

from __future__ import annotations

import numpy as np

from capturetrust import CaptureTrustConfig
from capturetrust.recapture import analyze_recapture


def test_score_bounded(patterned_image: np.ndarray) -> None:
    result = analyze_recapture(patterned_image, CaptureTrustConfig())
    assert 0.0 <= result["screen_recapture_score"] <= 1.0
    assert result["screen_recapture_risk"] in ("low", "medium", "high")


def test_warning_present_and_not_fraud_claim(patterned_image: np.ndarray) -> None:
    result = analyze_recapture(patterned_image, CaptureTrustConfig())
    warning = result["warning"].lower()
    assert "not proof" in warning
    assert "fraud" in warning  # phrased as "not ... fraud", never a claim
    # It must never assert the image *is* a recapture or fake.
    assert "fake" not in result["screen_recapture_risk"]


def test_patterned_image_raises_signal(patterned_image: np.ndarray) -> None:
    result = analyze_recapture(patterned_image, CaptureTrustConfig())
    # A dense periodic grid should produce a non-trivial line-pattern signal.
    assert result["line_pattern_score"] > 0.0


def test_flat_image_low_risk(blank_image: np.ndarray) -> None:
    result = analyze_recapture(blank_image, CaptureTrustConfig())
    assert result["screen_recapture_risk"] == "low"
