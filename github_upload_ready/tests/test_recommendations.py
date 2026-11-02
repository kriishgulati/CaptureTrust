"""Tests for the recommendation engine."""

from __future__ import annotations

from capturetrust.recommendations import build_issues_and_recommendations


def _checks(**overrides):
    base = {
        "blur": {"enabled": True, "passed": True, "severity": "none"},
        "lighting": {"enabled": True, "passed": True, "severity": "none", "label": "normal"},
        "glare": {"enabled": True, "passed": True, "severity": "none"},
        "screen_recapture": {"enabled": True, "passed": True, "risk": "low"},
    }
    base.update(overrides)
    return base


def test_blur_issue_and_recommendation() -> None:
    checks = _checks(blur={"enabled": True, "passed": False, "severity": "high"})
    issues, recs, _ = build_issues_and_recommendations(checks)
    assert "Image is blurry" in issues
    assert any("steady" in r for r in recs)


def test_dark_lighting_message() -> None:
    checks = _checks(
        lighting={"enabled": True, "passed": False, "severity": "high", "label": "dark"}
    )
    issues, _, _ = build_issues_and_recommendations(checks)
    assert "Image is too dark" in issues


def test_recommendations_deduplicated() -> None:
    checks = _checks(
        blur={"enabled": True, "passed": False, "severity": "high"},
    )
    issues, recs, _ = build_issues_and_recommendations(checks)
    assert len(recs) == len(set(recs))
    assert len(issues) == len(set(issues))


def test_recapture_warning_never_absent_when_enabled() -> None:
    _, _, warnings = build_issues_and_recommendations(_checks())
    assert any("experimental" in w.lower() for w in warnings)
