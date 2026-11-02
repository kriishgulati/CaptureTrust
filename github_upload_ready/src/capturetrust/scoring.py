"""Explainable, deterministic scoring engine.

The score starts at 100 and applies traceable deductions based on each
check's severity. Every deduction records the check, severity, amount and a
human-readable reason so the final number is fully auditable.
"""

from __future__ import annotations

from typing import Any

from .config import CaptureTrustConfig
from .types import Confidence

__all__ = ["DEFAULT_DEDUCTIONS", "compute_score", "confidence_label"]

# Default deductions keyed by check name then severity.
DEFAULT_DEDUCTIONS: dict[str, dict[str, int]] = {
    "blur": {"low": 8, "medium": 24, "high": 40},
    "resolution": {"low": 12, "medium": 16, "high": 20},
    "lighting": {"low": 7, "medium": 14, "high": 22},
    "glare": {"low": 8, "medium": 15, "high": 22},
    "noise": {"low": 5, "medium": 10, "high": 15},
    "shadow": {"low": 5, "medium": 10, "high": 16},
    "document_framing": {"low": 8, "medium": 16, "high": 25},
    "screen_recapture": {"medium": 10, "high": 20},
}

# Human-readable reasons attached to each deduction.
_REASONS: dict[str, str] = {
    "blur": "Low focus sharpness detected",
    "resolution": "Image resolution below the configured minimum",
    "lighting": "Exposure or lighting outside the acceptable range",
    "glare": "Large bright low-saturation regions detected",
    "noise": "Elevated high-frequency noise detected",
    "shadow": "Heavy shadow coverage detected",
    "document_framing": "Document framing or perspective issues detected",
    "screen_recapture": "Visual characteristics consistent with a screen recapture",
}


def _deduction_table(config: CaptureTrustConfig) -> dict[str, dict[str, int]]:
    table = {name: dict(levels) for name, levels in DEFAULT_DEDUCTIONS.items()}
    for name, overrides in config.deduction_overrides.items():
        table.setdefault(name, {}).update(overrides)
    return table


def compute_score(
    check_severities: list[tuple[str, str]],
    config: CaptureTrustConfig,
) -> dict[str, Any]:
    """Compute the final score and a full list of adjustments.

    Parameters
    ----------
    check_severities:
        Ordered ``(check_name, severity)`` pairs for every *enabled* check.
    config:
        Active configuration (used for deduction overrides).

    Returns
    -------
    dict
        ``{"starting_score", "adjustments", "final_score"}``.
    """
    table = _deduction_table(config)
    starting = 100
    remaining = starting
    adjustments: list[dict[str, Any]] = []

    for check_name, severity in check_severities:
        if severity in ("none", None):
            continue
        levels = table.get(check_name, {})
        deduction = int(levels.get(severity, 0))
        if deduction <= 0:
            continue
        # Never let a single deduction push the score below zero.
        applied = min(deduction, remaining)
        remaining -= applied
        adjustments.append(
            {
                "check": check_name,
                "severity": severity,
                "deduction": applied,
                "reason": _REASONS.get(check_name, "Quality issue detected"),
            }
        )
        if remaining <= 0:
            remaining = 0
            break

    final = max(0, min(100, remaining))
    return {
        "starting_score": starting,
        "adjustments": adjustments,
        "final_score": final,
    }


def confidence_label(final_score: int, signals_available: int) -> Confidence:
    """Derive a confidence label from the score and number of live signals.

    Confidence reflects how many independent checks contributed to the result,
    combined with how decisive the score is.
    """
    if signals_available <= 3:
        return "low"
    if signals_available >= 7 and (final_score >= 80 or final_score <= 40):
        return "high"
    return "medium"
