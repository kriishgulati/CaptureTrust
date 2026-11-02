"""Public inspection API.

:func:`inspect_image` and :func:`inspect_array` are the primary entry points.
They orchestrate every enabled check, assemble the metrics/checks tables,
run the scoring and recommendation engines, and return a
:class:`~capturetrust.report.CaptureTrustReport`.

Every individual check runs inside a guard so that a single failing optional
check degrades gracefully instead of aborting the whole inspection.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import (
    document as document_mod,
)
from . import (
    glare as glare_mod,
)
from . import (
    lighting as lighting_mod,
)
from . import (
    noise as noise_mod,
)
from . import (
    orientation as orientation_mod,
)
from . import (
    quality as quality_mod,
)
from . import (
    recapture as recapture_mod,
)
from . import (
    shadows as shadows_mod,
)
from . import (
    subject as subject_mod,
)
from .config import CaptureTrustConfig
from .recommendations import build_issues_and_recommendations
from .report import CaptureTrustReport
from .scoring import compute_score, confidence_label
from .types import BGRImage
from .utils import downscale_longest_side, load_image, normalize_image
from .version import __version__

__all__ = ["inspect_image", "inspect_array"]


def inspect_image(
    image_path: str | Path,
    *,
    config: CaptureTrustConfig | None = None,
) -> CaptureTrustReport:
    """Inspect an image file and return a quality report.

    Parameters
    ----------
    image_path:
        Path to an image file (jpg, png, webp, bmp, tiff, ...).
    config:
        Optional :class:`CaptureTrustConfig`. Defaults are used when omitted.
    """
    config = config or CaptureTrustConfig()
    image = load_image(image_path)
    return _run_inspection(image, config, source_type="file_path")


def inspect_array(
    image: np.ndarray,
    *,
    config: CaptureTrustConfig | None = None,
) -> CaptureTrustReport:
    """Inspect an in-memory image array (BGR, grayscale or BGRA)."""
    config = config or CaptureTrustConfig()
    normalized = normalize_image(image)
    return _run_inspection(normalized, config, source_type="numpy_array")


# --- orchestration ----------------------------------------------------------


def _run_inspection(
    image: BGRImage,
    config: CaptureTrustConfig,
    *,
    source_type: str,
) -> CaptureTrustReport:
    start = time.perf_counter()

    metrics: dict[str, Any] = {}
    checks: dict[str, dict[str, Any]] = {}
    scoring_pairs: list[tuple[str, str]] = []
    signals = 0

    height, width = image.shape[:2]
    metrics["width"] = int(width)
    metrics["height"] = int(height)

    # Detail-based checks run on a downscaled working image so sharpness/noise
    # are comparable across camera resolutions and processing stays fast. The
    # resolution check is the sole exception: it must see the true dimensions.
    work_image = downscale_longest_side(image, config.working_resolution)

    # Detect the main subject (face or document) once, so checks can focus on
    # it. Best-effort: if nothing confident is found, region is None and checks
    # fall back to their default behaviour.
    subject_region: tuple[float, float, float, float] | None = None
    subject_type: str | None = None
    if config.enable_subject_detection:
        try:
            found = subject_mod.detect_subject(work_image, config)
            subject_region = found.get("region")  # type: ignore[assignment]
            subject_type = found.get("subject_type")  # type: ignore[assignment]
        except Exception:  # noqa: BLE001 - detection is best-effort only
            subject_region = None
            subject_type = None
    metrics["subject_detected"] = subject_type is not None
    metrics["subject_type"] = subject_type

    def run(
        name: str,
        enabled: bool,
        func: Callable[[BGRImage, CaptureTrustConfig], dict[str, Any]],
        on_success: Callable[[dict[str, Any]], dict[str, Any]],
        score_key: str,
        *,
        use_original: bool = False,
    ) -> None:
        nonlocal signals
        if not enabled:
            checks[name] = {"enabled": False, "passed": True, "severity": "none"}
            return
        target = image if use_original else work_image
        try:
            raw = func(target, config)
        except Exception as exc:  # noqa: BLE001 - checks must fail safely
            checks[name] = {
                "enabled": True,
                "passed": True,
                "severity": "none",
                "error": f"{type(exc).__name__}: {exc}",
            }
            return
        signals += 1
        entry = on_success(raw)
        checks[name] = entry
        severity = str(entry.get("severity", "none"))
        if not entry.get("passed", True):
            scoring_pairs.append((score_key, severity))

    # --- Blur ---
    def _blur(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["blur_score"] = raw["blur_score"]
        metrics["tenengrad_score"] = raw["tenengrad_score"]
        metrics["center_edge_density"] = raw["center_edge_density"]
        metrics["center_laplacian_variance"] = raw["center_laplacian_variance"]
        metrics["directionality"] = raw.get("directionality")
        metrics["edge_crispness"] = raw.get("edge_crispness")
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "score": raw["blur_score"],
        }

    def _blur_check(img: BGRImage, cfg: CaptureTrustConfig) -> dict[str, Any]:
        return quality_mod.analyze_blur(img, cfg, region=subject_region)

    run("blur", config.enable_blur_check, _blur_check, _blur, "blur")

    # --- Resolution ---
    def _resolution(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["megapixels"] = raw["megapixels"]
        metrics["aspect_ratio"] = raw["aspect_ratio"]
        metrics["aspect_ratio_label"] = raw["aspect_ratio_label"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "is_low_resolution": raw["is_low_resolution"],
        }

    run(
        "resolution",
        config.enable_resolution_check,
        quality_mod.analyze_resolution,
        _resolution,
        "resolution",
        use_original=True,
    )

    # --- Lighting ---
    def _lighting(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["average_brightness"] = raw["average_brightness"]
        metrics["median_brightness"] = raw["median_brightness"]
        metrics["dark_pixel_ratio"] = raw["dark_pixel_ratio"]
        metrics["bright_pixel_ratio"] = raw["bright_pixel_ratio"]
        metrics["dynamic_range"] = raw["dynamic_range"]
        metrics["brightness_label"] = raw["brightness_label"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "label": raw["brightness_label"],
        }

    run(
        "lighting",
        config.enable_lighting_check,
        lighting_mod.analyze_lighting,
        _lighting,
        "lighting",
    )

    # --- Glare ---
    def _glare(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["glare_ratio"] = raw["glare_ratio"]
        metrics["largest_glare_region_ratio"] = raw["largest_glare_region_ratio"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "glare_ratio": raw["glare_ratio"],
        }

    run("glare", config.enable_glare_check, glare_mod.analyze_glare, _glare, "glare")

    # --- Noise ---
    def _noise(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["noise_score"] = raw["noise_score"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "noise_score": raw["noise_score"],
        }

    run("noise", config.enable_noise_check, noise_mod.analyze_noise, _noise, "noise")

    # --- Shadow ---
    def _shadow(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["shadow_ratio"] = raw["shadow_ratio"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "shadow_ratio": raw["shadow_ratio"],
        }

    run("shadow", config.enable_shadow_check, shadows_mod.analyze_shadows, _shadow, "shadow")

    # --- Orientation ---
    def _orientation(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["estimated_rotation_degrees"] = raw["estimated_rotation_degrees"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": severity == "none",
            "severity": severity,
            "estimated_rotation_degrees": raw["estimated_rotation_degrees"],
        }

    run(
        "orientation",
        config.enable_orientation_check,
        orientation_mod.analyze_orientation,
        _orientation,
        "orientation",
    )

    # --- Document framing ---
    def _document(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["document_detected"] = raw["document_detected"]
        metrics["document_area_ratio"] = raw["document_area_ratio"]
        metrics["document_corners_visible"] = raw["document_corners_visible"]
        metrics["document_tilt_degrees"] = raw["document_tilt_degrees"]
        metrics["perspective_distortion_score"] = raw["perspective_distortion_score"]
        severity = raw["severity"]
        # A framing issue only "fails" when a document was actually detected.
        passed = severity == "none" or not raw["document_detected"]
        return {
            "enabled": True,
            "passed": passed,
            "severity": severity if raw["document_detected"] else "none",
            "document_detected": raw["document_detected"],
            "edges_cut_off": bool(raw["document_edges_cut_off"])
            if raw["document_edges_cut_off"] is not None
            else False,
        }

    run(
        "document",
        config.enable_document_check,
        document_mod.analyze_document,
        _document,
        "document_framing",
    )

    # --- Screen recapture (experimental) ---
    def _recapture(raw: dict[str, Any]) -> dict[str, Any]:
        metrics["screen_recapture_score"] = raw["screen_recapture_score"]
        metrics["screen_recapture_risk"] = raw["screen_recapture_risk"]
        severity = raw["severity"]
        return {
            "enabled": True,
            "passed": raw["screen_recapture_risk"] == "low",
            "severity": severity,
            "risk": raw["screen_recapture_risk"],
            "score": raw["screen_recapture_score"],
            "warning": raw["warning"],
        }

    run(
        "screen_recapture",
        config.enable_screen_recapture_check,
        recapture_mod.analyze_recapture,
        _recapture,
        "screen_recapture",
    )

    # --- Scoring ---
    scoring = compute_score(scoring_pairs, config)
    final_score = int(scoring["final_score"])
    metrics["score_explanation"] = scoring

    issues, recommendations, warnings = build_issues_and_recommendations(checks)
    confidence = confidence_label(final_score, signals)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    metadata = {
        "library_version": __version__,
        "image_source_type": source_type,
        "processing_time_ms": round(elapsed_ms, 3),
        "signals_available": signals,
    }

    is_acceptable = final_score >= config.acceptable_score
    if config.reject_blurry and checks.get("blur", {}).get("severity") in ("medium", "high"):
        # A photo the blur check considers clearly blurry should not pass,
        # regardless of the numeric score.
        is_acceptable = False

    return CaptureTrustReport(
        score=final_score,
        is_acceptable=is_acceptable,
        confidence=confidence,
        issues=issues,
        recommendations=recommendations,
        warnings=warnings,
        metrics=metrics,
        checks=checks,
        metadata=metadata,
    )
