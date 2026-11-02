"""Shared pytest fixtures: synthetic image generators.

These helpers build small NumPy images with known characteristics so the
checks can be exercised deterministically without bundling binary assets.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest


def _seeded(shape: tuple[int, ...], low: int, high: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(low, high, size=shape, dtype=np.uint8)


@pytest.fixture
def blank_image() -> np.ndarray:
    """A flat mid-gray image."""
    return np.full((600, 800, 3), 128, dtype=np.uint8)


@pytest.fixture
def dark_image() -> np.ndarray:
    """A very dark, underexposed image."""
    return np.full((600, 800, 3), 18, dtype=np.uint8)


@pytest.fixture
def bright_image() -> np.ndarray:
    """A very bright, overexposed image."""
    return np.full((600, 800, 3), 245, dtype=np.uint8)


@pytest.fixture
def sharp_image() -> np.ndarray:
    """A well-exposed, high-detail image with crisp fine texture in the centre."""
    rng = np.random.default_rng(7)
    base = np.full((900, 1200, 3), 130, dtype=np.uint8)
    cv2.circle(base, (600, 450), 220, (90, 160, 210), -1)
    cv2.rectangle(base, (150, 150), (520, 640), (200, 180, 120), -1)
    # Strong high-frequency texture across the frame, like real subject detail,
    # so the centre-region sharpness reflects a genuinely crisp photo.
    texture = rng.integers(0, 110, (900, 1200, 3), dtype=np.int16).astype(np.uint8)
    return cv2.addWeighted(base, 0.6, texture, 0.4, 0)


@pytest.fixture
def blurry_image(sharp_image: np.ndarray) -> np.ndarray:
    """A heavily blurred version of the sharp image."""
    return cv2.GaussianBlur(sharp_image, (31, 31), 0)


@pytest.fixture
def low_resolution_image() -> np.ndarray:
    """A tiny image, well below any sensible minimum."""
    return np.full((120, 160, 3), 128, dtype=np.uint8)


@pytest.fixture
def glare_image() -> np.ndarray:
    """A mid-tone image with a large blown-out low-saturation patch (~35% of the frame)."""
    img = np.full((600, 800, 3), 90, dtype=np.uint8)
    cv2.rectangle(img, (150, 100), (650, 500), (252, 252, 252), -1)
    return img


@pytest.fixture
def shadow_image() -> np.ndarray:
    """A brightly lit image with a large dark shadow region."""
    img = np.full((600, 800, 3), 180, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (360, 600), (35, 35, 35), -1)
    return img


@pytest.fixture
def rotated_document_image() -> np.ndarray:
    """A light document quadrilateral rotated on a dark background."""
    img = np.full((900, 1200, 3), 30, dtype=np.uint8)
    pts = np.array([[330, 250], [880, 300], [840, 720], [290, 660]], dtype=np.int32)
    cv2.fillConvexPoly(img, pts, (235, 235, 235))
    cv2.polylines(img, [pts], True, (10, 10, 10), 3)
    return img


@pytest.fixture
def document_image() -> np.ndarray:
    """A well-framed, axis-aligned document on a dark background."""
    img = np.full((900, 1200, 3), 25, dtype=np.uint8)
    cv2.rectangle(img, (200, 150), (1000, 760), (240, 240, 240), -1)
    cv2.rectangle(img, (200, 150), (1000, 760), (5, 5, 5), 3)
    for y in range(220, 720, 60):
        cv2.line(img, (260, y), (940, y), (120, 120, 120), 4)
    return img


@pytest.fixture
def patterned_image() -> np.ndarray:
    """A strongly periodic line pattern (screen-recapture-like texture)."""
    img = np.full((600, 800, 3), 128, dtype=np.uint8)
    for x in range(0, 800, 4):
        cv2.line(img, (x, 0), (x, 600), (60, 60, 60), 1)
    for y in range(0, 600, 4):
        cv2.line(img, (0, y), (800, y), (60, 60, 60), 1)
    return img


@pytest.fixture
def grayscale_image() -> np.ndarray:
    """A single-channel grayscale image."""
    return _seeded((600, 800), 40, 210, seed=3)


@pytest.fixture
def rgba_image() -> np.ndarray:
    """A 4-channel BGRA image."""
    bgr = _seeded((600, 800, 3), 40, 210, seed=5)
    alpha = np.full((600, 800, 1), 255, dtype=np.uint8)
    return np.concatenate([bgr, alpha], axis=2)
