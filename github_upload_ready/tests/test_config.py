"""Tests for CaptureTrustConfig validation."""

from __future__ import annotations

import pytest

from capturetrust import CaptureTrustConfig
from capturetrust.exceptions import InvalidConfigurationError


def test_defaults_valid() -> None:
    config = CaptureTrustConfig()
    assert config.min_width > 0
    assert 0 <= config.acceptable_score <= 100


@pytest.mark.parametrize("field", ["min_width", "min_height"])
def test_non_positive_dimensions_rejected(field: str) -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(**{field: 0})


@pytest.mark.parametrize("score", [-1, 101, 200])
def test_score_out_of_range_rejected(score: int) -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(acceptable_score=score)


@pytest.mark.parametrize("ratio", [-0.1, 1.1, 2.0])
def test_ratio_out_of_range_rejected(ratio: float) -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(glare_threshold=ratio)


def test_brightness_order_enforced() -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(dark_brightness_threshold=200.0, bright_brightness_threshold=100.0)


def test_recapture_threshold_order_enforced() -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(
            screen_recapture_medium_threshold=0.8,
            screen_recapture_high_threshold=0.4,
        )


def test_blur_threshold_must_be_positive() -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(blur_threshold=0.0)


def test_toggle_must_be_bool() -> None:
    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(enable_blur_check="yes")  # type: ignore[arg-type]


def test_to_dict_roundtrip() -> None:
    config = CaptureTrustConfig(min_width=1024, min_height=768)
    data = config.to_dict()
    assert data["min_width"] == 1024
    assert data["min_height"] == 768


def test_working_resolution_default() -> None:
    assert CaptureTrustConfig().working_resolution == 1024


def test_working_resolution_must_be_reasonable() -> None:
    import pytest

    from capturetrust.exceptions import InvalidConfigurationError

    with pytest.raises(InvalidConfigurationError):
        CaptureTrustConfig(working_resolution=100)


def test_subject_detection_off_by_default() -> None:
    assert CaptureTrustConfig().enable_subject_detection is False


def test_heic_in_supported_suffixes() -> None:
    from capturetrust.utils import SUPPORTED_SUFFIXES

    assert ".heic" in SUPPORTED_SUFFIXES


def test_presets_construct_and_differ() -> None:
    docs = CaptureTrustConfig.for_documents()
    photos = CaptureTrustConfig.for_photos()
    balanced = CaptureTrustConfig.balanced()
    assert docs.blur_threshold > photos.blur_threshold
    assert docs.enable_document_check is True
    assert photos.enable_document_check is False
    assert balanced.blur_threshold == CaptureTrustConfig().blur_threshold


def test_preset_overrides_apply() -> None:
    cfg = CaptureTrustConfig.for_photos(acceptable_score=50)
    assert cfg.acceptable_score == 50
