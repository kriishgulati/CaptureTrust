"""Tests for the scoring engine."""

from __future__ import annotations

from capturetrust import CaptureTrustConfig
from capturetrust.scoring import compute_score, confidence_label


def test_perfect_image_scores_100() -> None:
    result = compute_score([], CaptureTrustConfig())
    assert result["final_score"] == 100
    assert result["adjustments"] == []


def test_deductions_applied() -> None:
    result = compute_score([("blur", "high"), ("glare", "medium")], CaptureTrustConfig())
    assert result["final_score"] == 100 - 40 - 15
    assert len(result["adjustments"]) == 2


def test_score_never_negative() -> None:
    pairs = [("blur", "high")] * 20
    result = compute_score(pairs, CaptureTrustConfig())
    assert result["final_score"] >= 0


def test_adjustments_are_traceable() -> None:
    result = compute_score([("blur", "high")], CaptureTrustConfig())
    adj = result["adjustments"][0]
    assert adj["check"] == "blur"
    assert adj["severity"] == "high"
    assert adj["deduction"] == 40
    assert "reason" in adj


def test_deduction_overrides() -> None:
    config = CaptureTrustConfig(deduction_overrides={"blur": {"high": 5}})
    result = compute_score([("blur", "high")], config)
    assert result["final_score"] == 95


def test_confidence_label() -> None:
    assert confidence_label(90, 8) == "high"
    assert confidence_label(60, 2) == "low"
    assert confidence_label(60, 6) == "medium"
