"""Recommendation engine.

Maps detected issues to specific, friendly, deduplicated guidance. Each issue
string is paired with a recommendation; :func:`build_issues_and_recommendations`
consumes the raw check results and produces ordered, de-duplicated lists of
issues, recommendations and warnings for the report.
"""

from __future__ import annotations

from typing import Any

__all__ = ["build_issues_and_recommendations"]

# Careful, non-accusatory wording. Note the deliberate avoidance of words like
# "fake", "fraudulent" or "tampered".
_RECAPTURE_WARNING = "Screen recapture analysis is experimental and should not be treated as proof."


def build_issues_and_recommendations(
    checks: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    """Return ``(issues, recommendations, warnings)`` from check results.

    Only *enabled* checks that actually failed contribute entries. Order is
    stable and duplicates are removed.
    """
    issues: list[str] = []
    recommendations: list[str] = []
    warnings: list[str] = []

    def add(issue: str, recommendation: str) -> None:
        if issue not in issues:
            issues.append(issue)
        if recommendation not in recommendations:
            recommendations.append(recommendation)

    # --- Blur ---
    blur = checks.get("blur")
    if blur and blur.get("enabled") and not blur.get("passed"):
        if blur.get("severity") == "low":
            add(
                "Image is slightly soft",
                "For best results, hold the camera steady and let it focus before capturing.",
            )
        else:
            add(
                "Image is blurry",
                "Retake the image while holding the camera steady and ensuring the "
                "subject is in focus.",
            )

    # --- Resolution ---
    resolution = checks.get("resolution")
    if resolution and resolution.get("enabled") and not resolution.get("passed"):
        add(
            "Image is low resolution",
            "Upload a higher-resolution image or avoid screenshots that reduce detail.",
        )

    # --- Lighting ---
    lighting = checks.get("lighting")
    if lighting and lighting.get("enabled") and not lighting.get("passed"):
        label = lighting.get("label")
        if label in ("dark", "very_dark"):
            add(
                "Image is too dark",
                "Use brighter, even lighting and avoid placing the subject in shadow.",
            )
        elif label in ("bright", "very_bright"):
            add(
                "Image is overexposed",
                "Move away from direct light or reduce glare before retaking the image.",
            )
        else:
            add(
                "Image has uneven lighting",
                "Use even, diffuse lighting so the whole subject is lit consistently.",
            )

    # --- Glare ---
    glare = checks.get("glare")
    if glare and glare.get("enabled") and not glare.get("passed"):
        add(
            "Strong glare detected",
            "Change the camera angle or move away from direct light to reduce glare.",
        )

    # --- Noise ---
    noise = checks.get("noise")
    if noise and noise.get("enabled") and not noise.get("passed"):
        add(
            "Image appears noisy",
            "Use better lighting or a lower camera ISO setting to reduce graininess.",
        )

    # --- Shadow ---
    shadow = checks.get("shadow")
    if shadow and shadow.get("enabled") and not shadow.get("passed"):
        add(
            "Heavy shadows detected",
            "Reposition the light source or subject to avoid strong shadows.",
        )

    # --- Orientation ---
    orientation = checks.get("orientation")
    if orientation and orientation.get("enabled") and not orientation.get("passed"):
        add(
            "Image may be rotated or skewed",
            "Align the camera squarely with the subject and hold it level.",
        )

    # --- Document framing ---
    document = checks.get("document")
    if document and document.get("enabled") and not document.get("passed"):
        if document.get("edges_cut_off"):
            add(
                "Document edges may be cut off",
                "Keep all four corners of the document fully visible inside the frame.",
            )
        else:
            add(
                "Document framing may be incomplete",
                "Place the document flat and fill the frame while keeping all corners visible.",
            )

    # --- Screen recapture (experimental) ---
    recapture = checks.get("screen_recapture")
    if recapture and recapture.get("enabled"):
        if recapture.get("risk") in ("medium", "high"):
            add(
                "Possible screen recapture signal",
                "Use the original file rather than photographing a phone, tablet, "
                "or computer display.",
            )
        if _RECAPTURE_WARNING not in warnings:
            warnings.append(_RECAPTURE_WARNING)

    return issues, recommendations, warnings
