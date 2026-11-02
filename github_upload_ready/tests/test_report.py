"""Tests for the CaptureTrustReport object."""

from __future__ import annotations

import json

import numpy as np

from capturetrust import CaptureTrustReport, inspect_array


def test_to_dict_keys(sharp_image: np.ndarray) -> None:
    report = inspect_array(sharp_image)
    data = report.to_dict()
    for key in (
        "score",
        "is_acceptable",
        "confidence",
        "issues",
        "recommendations",
        "warnings",
        "metrics",
        "checks",
        "metadata",
    ):
        assert key in data


def test_to_json_is_valid(sharp_image: np.ndarray) -> None:
    report = inspect_array(sharp_image)
    parsed = json.loads(report.to_json())
    assert parsed["score"] == report.score


def test_to_json_no_numpy_types(dark_image: np.ndarray) -> None:
    # json.dumps would raise if numpy scalars leaked through unconverted.
    report = inspect_array(dark_image)
    text = report.to_json(indent=0)
    assert isinstance(text, str)
    json.loads(text)


def test_summary_is_readable(dark_image: np.ndarray) -> None:
    report = inspect_array(dark_image)
    summary = report.summary()
    assert "CaptureTrust score" in summary
    assert "not a fraud decision" in summary


def test_manual_report_construction() -> None:
    report = CaptureTrustReport(score=80, is_acceptable=True, confidence="high")
    assert report.to_dict()["score"] == 80
    assert report.issues == []
