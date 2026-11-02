"""Configuration for CaptureTrust inspections.

The :class:`CaptureTrustConfig` dataclass exposes every tunable threshold and
feature toggle so that advanced users can adapt the library to their own
acceptance criteria without editing library code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .exceptions import InvalidConfigurationError

__all__ = ["CaptureTrustConfig"]


@dataclass
class CaptureTrustConfig:
    """Tunable thresholds and feature toggles for an inspection.

    All fields have sensible defaults. Every field is validated in
    :meth:`__post_init__`; invalid values raise
    :class:`~capturetrust.exceptions.InvalidConfigurationError`.
    """

    # --- Resolution ---
    min_width: int = 640
    min_height: int = 480

    # --- Working resolution ---
    # Detail-based checks are measured after downscaling so the longest side is
    # at most this many pixels. This makes sharpness/noise comparable across
    # cameras and keeps processing fast. The resolution check still reports the
    # image's true, original dimensions.
    working_resolution: int = 1024

    # --- Blur ---
    # Boundary on the centre-region Laplacian variance (measured at working
    # resolution) at or above which the subject is considered acceptably sharp.
    # Calibrated against a labelled set of real photos; see docs/limitations.
    blur_threshold: float = 280.0

    # --- Lighting ---
    dark_brightness_threshold: float = 60.0
    bright_brightness_threshold: float = 190.0

    # --- Glare ---
    # Fraction of the frame that is bright + low-saturation before glare is
    # flagged. Naturally bright, pale content (overcast sky, pale pavement,
    # white paper/clothing) is common in legitimate photos and is not a
    # defect, so the bar sits above what ordinary bright scenes reach.
    # Calibrated against 60 labelled good photos (no glare occurred below
    # 0.20; two legitimate bright outdoor photos peaked at 0.335-0.337) - not
    # yet validated against genuine bad-glare examples, since none exist in
    # the labelled set. If precise glare calibration matters for your use
    # case, provide examples of photos that are unusable due to glare.
    glare_threshold: float = 0.20

    # --- Acceptance ---
    acceptable_score: int = 70
    # When True, an image the blur check rates medium/high is never marked
    # acceptable, even if its numeric score clears acceptable_score. Blur is the
    # primary quality failure for OCR/document/upload use cases, so a photo the
    # tool itself considers blurry should not pass a quality gate.
    reject_blurry: bool = True

    # --- Feature toggles ---
    enable_blur_check: bool = True
    enable_resolution_check: bool = True
    enable_lighting_check: bool = True
    enable_glare_check: bool = True
    enable_document_check: bool = True
    # Experimental and OFF by default: on real-world photos this heuristic has a
    # high false-positive rate (ornate objects, textures and printed patterns
    # trip it), and it cannot be reliably calibrated without a labelled set of
    # genuine screen recaptures. Opt in explicitly if you want to experiment.
    enable_screen_recapture_check: bool = False
    enable_noise_check: bool = True
    enable_shadow_check: bool = True
    enable_orientation_check: bool = True
    # Focus blur on a detected face or document instead of the centre region.
    # OFF by default: measured against a labelled photo set it did not improve
    # accuracy (face detection via the bundled Haar cascade is unreliable, and a
    # heavily-blurred subject cannot be detected at all). Opt in to experiment;
    # it falls back safely to centre-region analysis when no subject is found.
    enable_subject_detection: bool = False

    # --- Document framing ---
    document_min_area_ratio: float = 0.15
    document_edge_margin_ratio: float = 0.03

    # --- Screen recapture ---
    screen_recapture_medium_threshold: float = 0.40
    screen_recapture_high_threshold: float = 0.70

    # Custom scoring deduction overrides (optional). When empty the built-in
    # defaults from :mod:`capturetrust.scoring` are used.
    deduction_overrides: dict[str, dict[str, int]] = field(default_factory=dict)

    # --- Presets ---
    # Ready-made configurations for common contexts. One fixed threshold cannot
    # serve both a strict document scan and a lenient artistic photo (a sharp
    # subject with a blurred background and a blurry subject with a sharp
    # background are near-indistinguishable in pixels), so the caller chooses
    # the context that matches their content.

    @classmethod
    def for_documents(cls, **overrides: object) -> CaptureTrustConfig:
        """Strict profile for documents, receipts and ID cards (OCR-ready).

        Requires genuinely sharp, well-framed pages; smooth or artistically
        soft images are rejected, which is correct for this use.
        """
        params: dict[str, object] = {
            "blur_threshold": 280.0,
            "acceptable_score": 75,
            "min_width": 1000,
            "min_height": 1000,
            "enable_document_check": True,
            "reject_blurry": True,
        }
        params.update(overrides)
        return cls(**params)  # type: ignore[arg-type]

    @classmethod
    def for_photos(cls, **overrides: object) -> CaptureTrustConfig:
        """Lenient profile for general and artistic photography.

        Accepts smooth subjects and shallow depth-of-field (bokeh) - a flower
        in focus against a blurred background passes - while still rejecting
        photos that are clearly blurry throughout.
        """
        params: dict[str, object] = {
            "blur_threshold": 110.0,
            "acceptable_score": 60,
            "enable_document_check": False,
            "reject_blurry": True,
        }
        params.update(overrides)
        return cls(**params)  # type: ignore[arg-type]

    @classmethod
    def balanced(cls, **overrides: object) -> CaptureTrustConfig:
        """General-purpose profile (the default settings)."""
        return cls(**overrides)  # type: ignore[arg-type]

    def __post_init__(self) -> None:
        """Validate all fields, raising on any inconsistency."""
        self._require_positive_int("min_width", self.min_width)
        self._require_positive_int("min_height", self.min_height)

        self._require_positive_int("working_resolution", self.working_resolution)
        if self.working_resolution < 256:
            raise InvalidConfigurationError(
                f"working_resolution must be at least 256 (got {self.working_resolution})."
            )

        self._require_positive_number("blur_threshold", self.blur_threshold)

        self._require_range("dark_brightness_threshold", self.dark_brightness_threshold, 0.0, 255.0)
        self._require_range(
            "bright_brightness_threshold", self.bright_brightness_threshold, 0.0, 255.0
        )
        if self.dark_brightness_threshold >= self.bright_brightness_threshold:
            raise InvalidConfigurationError(
                "dark_brightness_threshold must be strictly less than "
                "bright_brightness_threshold "
                f"(got {self.dark_brightness_threshold} >= {self.bright_brightness_threshold})."
            )

        self._require_ratio("glare_threshold", self.glare_threshold)
        self._require_ratio("document_min_area_ratio", self.document_min_area_ratio)
        self._require_ratio("document_edge_margin_ratio", self.document_edge_margin_ratio)
        self._require_ratio(
            "screen_recapture_medium_threshold", self.screen_recapture_medium_threshold
        )
        self._require_ratio("screen_recapture_high_threshold", self.screen_recapture_high_threshold)
        if self.screen_recapture_medium_threshold >= self.screen_recapture_high_threshold:
            raise InvalidConfigurationError(
                "screen_recapture_medium_threshold must be strictly less than "
                "screen_recapture_high_threshold "
                f"(got {self.screen_recapture_medium_threshold} >= "
                f"{self.screen_recapture_high_threshold})."
            )

        if not 0 <= self.acceptable_score <= 100:
            raise InvalidConfigurationError(
                f"acceptable_score must be between 0 and 100 (got {self.acceptable_score})."
            )

        for name, value in (
            ("enable_blur_check", self.enable_blur_check),
            ("enable_resolution_check", self.enable_resolution_check),
            ("enable_lighting_check", self.enable_lighting_check),
            ("enable_glare_check", self.enable_glare_check),
            ("enable_document_check", self.enable_document_check),
            ("enable_screen_recapture_check", self.enable_screen_recapture_check),
            ("enable_noise_check", self.enable_noise_check),
            ("enable_shadow_check", self.enable_shadow_check),
            ("enable_orientation_check", self.enable_orientation_check),
        ):
            if not isinstance(value, bool):
                raise InvalidConfigurationError(f"{name} must be a boolean (got {value!r}).")

    # --- validation helpers -------------------------------------------------

    @staticmethod
    def _require_positive_int(name: str, value: Any) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise InvalidConfigurationError(f"{name} must be a positive integer (got {value!r}).")

    @staticmethod
    def _require_positive_number(name: str, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise InvalidConfigurationError(f"{name} must be a positive number (got {value!r}).")

    @staticmethod
    def _require_ratio(name: str, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidConfigurationError(f"{name} must be a number (got {value!r}).")
        if not 0.0 <= float(value) <= 1.0:
            raise InvalidConfigurationError(f"{name} must be between 0 and 1 (got {value}).")

    @staticmethod
    def _require_range(name: str, value: Any, low: float, high: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidConfigurationError(f"{name} must be a number (got {value!r}).")
        if not low <= float(value) <= high:
            raise InvalidConfigurationError(
                f"{name} must be between {low} and {high} (got {value})."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return the configuration as a plain dictionary."""
        return asdict(self)
