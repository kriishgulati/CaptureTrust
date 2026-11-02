"""Tests for batch inspection."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from capturetrust import CaptureTrustReport, inspect_batch


def _write(tmp_path: Path, name: str, image: np.ndarray) -> Path:
    path = tmp_path / name
    cv2.imwrite(str(path), image)
    return path


def test_batch_order_preserved(tmp_path: Path, sharp_image, dark_image) -> None:
    p1 = _write(tmp_path, "a.png", sharp_image)
    p2 = _write(tmp_path, "b.png", dark_image)
    reports = inspect_batch([p1, p2])
    assert len(reports) == 2
    assert all(isinstance(r, CaptureTrustReport) for r in reports)
    # The dark image should score lower than the sharp one.
    assert reports[1].score < reports[0].score


def test_batch_concurrent_matches_serial(tmp_path: Path, sharp_image, dark_image) -> None:
    paths = [
        _write(tmp_path, "a.png", sharp_image),
        _write(tmp_path, "b.png", dark_image),
    ]
    serial = inspect_batch(paths, workers=1)
    parallel = inspect_batch(paths, workers=2)
    assert [r.score for r in serial] == [r.score for r in parallel]


def test_invalid_workers_rejected(tmp_path: Path, sharp_image) -> None:
    path = _write(tmp_path, "a.png", sharp_image)
    with pytest.raises(ValueError):
        inspect_batch([path], workers=0)


def test_empty_batch() -> None:
    assert inspect_batch([]) == []
