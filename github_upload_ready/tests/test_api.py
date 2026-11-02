"""Tests for the public inspection API."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

import capturetrust
from capturetrust import (
    CaptureTrustConfig,
    CaptureTrustReport,
    inspect_array,
    inspect_image,
)
from capturetrust.exceptions import (
    ImageReadError,
    InvalidImageError,
    UnsupportedImageFormatError,
)


def test_package_imports() -> None:
    for name in (
        "inspect_image",
        "inspect_array",
        "inspect_batch",
        "CaptureTrustReport",
        "CaptureTrustConfig",
    ):
        assert hasattr(capturetrust, name)
    assert isinstance(capturetrust.__version__, str)


def test_inspect_array_returns_report(sharp_image: np.ndarray) -> None:
    report = inspect_array(sharp_image)
    assert isinstance(report, CaptureTrustReport)
    assert 0 <= report.score <= 100
    assert isinstance(report.is_acceptable, bool)
    assert report.confidence in ("low", "medium", "high")


def test_inspect_image_from_path(tmp_path: Path, sharp_image: np.ndarray) -> None:
    path = tmp_path / "sharp.png"
    cv2.imwrite(str(path), sharp_image)
    report = inspect_image(path)
    assert report.metadata["image_source_type"] == "file_path"
    assert report.metrics["width"] == sharp_image.shape[1]


def test_grayscale_input(grayscale_image: np.ndarray) -> None:
    report = inspect_array(grayscale_image)
    assert report.metrics["width"] == grayscale_image.shape[1]


def test_rgba_input(rgba_image: np.ndarray) -> None:
    report = inspect_array(rgba_image)
    assert report.metrics["width"] == rgba_image.shape[1]


def test_invalid_path_raises() -> None:
    with pytest.raises(ImageReadError):
        inspect_image("does-not-exist-12345.jpg")


def test_empty_array_raises() -> None:
    with pytest.raises(InvalidImageError):
        inspect_array(np.zeros((0, 0, 3), dtype=np.uint8))


def test_unsupported_dtype_raises() -> None:
    with pytest.raises(UnsupportedImageFormatError):
        inspect_array(np.zeros((10, 10, 3), dtype=np.complex64))


def test_input_array_not_mutated(sharp_image: np.ndarray) -> None:
    before = sharp_image.copy()
    inspect_array(sharp_image)
    assert np.array_equal(sharp_image, before)


def test_deterministic(sharp_image: np.ndarray) -> None:
    a = inspect_array(sharp_image)
    b = inspect_array(sharp_image)
    assert a.score == b.score

    # Everything except wall-clock timing must be identical.
    da, db = a.to_dict(), b.to_dict()
    da["metadata"].pop("processing_time_ms")
    db["metadata"].pop("processing_time_ms")
    assert da == db


def test_disabled_checks_recorded(sharp_image: np.ndarray) -> None:
    config = CaptureTrustConfig(enable_document_check=False, enable_screen_recapture_check=False)
    report = inspect_array(sharp_image, config=config)
    assert report.checks["document"]["enabled"] is False
    assert report.checks["screen_recapture"]["enabled"] is False


def test_one_failing_check_does_not_crash(monkeypatch, sharp_image: np.ndarray) -> None:
    import capturetrust.api as api

    def boom(_image, _config):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(api.glare_mod, "analyze_glare", boom)
    report = inspect_array(sharp_image)
    assert "error" in report.checks["glare"]
    assert report.checks["glare"]["passed"] is True
