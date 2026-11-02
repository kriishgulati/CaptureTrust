"""Image loading and normalisation utilities.

Everything downstream of these helpers can assume it receives a contiguous
3-channel ``uint8`` BGR image, which keeps the individual check modules
simple and predictable.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .exceptions import (
    ImageReadError,
    InvalidImageError,
    UnsupportedImageFormatError,
)
from .types import BGRImage

__all__ = [
    "load_image",
    "normalize_image",
    "to_grayscale",
    "downscale_longest_side",
    "SUPPORTED_SUFFIXES",
]

# File suffixes the CLI batch mode is willing to scan for.
SUPPORTED_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif"}
)

_HEIF_SUFFIXES = frozenset({".heic", ".heif"})

_MAX_UINT8 = 255.0


def load_image(image_path: str | Path) -> BGRImage:
    """Load an image file from disk as a normalised BGR ``uint8`` array.

    EXIF orientation is always applied: phones commonly store a photo's raw
    sensor pixels in one orientation with a rotation tag saying how to display
    it. Ignoring that tag would measure blur, framing and lighting on the
    wrong orientation entirely - not a minor discrepancy, since the "subject"
    region the checks focus on would no longer line up with where the subject
    actually is.

    Parameters
    ----------
    image_path:
        Path to an image file.

    Returns
    -------
    numpy.ndarray
        A contiguous 3-channel BGR ``uint8`` image, EXIF-rotated upright.

    Raises
    ------
    ImageReadError
        If the file does not exist or cannot be decoded.
    """
    path = Path(image_path)
    if not path.exists():
        raise ImageReadError(f"Image file does not exist: {path}")
    if not path.is_file():
        raise ImageReadError(f"Path is not a file: {path}")

    if path.suffix.lower() in _HEIF_SUFFIXES:
        return normalize_image(_decode_heif(path))

    try:
        from PIL import Image, ImageOps

        with Image.open(path) as im:
            transposed = ImageOps.exif_transpose(im)  # apply rotation tag, if any
            rgb = np.asarray(
                transposed.convert("RGB") if transposed is not None else im.convert("RGB")
            )
        image: np.ndarray | None = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        # Fall back to the raw decoder for formats PIL cannot open. This path
        # does not apply EXIF orientation, since cv2 has no EXIF-aware decode.
        try:
            data = np.fromfile(str(path), dtype=np.uint8)
        except OSError as exc:  # pragma: no cover - filesystem dependent
            raise ImageReadError(f"Could not read image file: {path} ({exc})") from exc
        if data.size == 0:
            raise ImageReadError(f"Image file is empty: {path}") from None
        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ImageReadError(
                f"Could not decode image (unsupported or corrupt file): {path}"
            ) from None

    assert image is not None  # narrowed by the raises above; for mypy
    return normalize_image(image)


def _decode_heif(path: Path) -> np.ndarray:
    """Decode a HEIC/HEIF image (e.g. from an iPhone) into a BGR array."""
    try:
        import pillow_heif
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise UnsupportedImageFormatError(
            "Reading HEIC/HEIF images requires the 'pillow-heif' package. "
            "Install it with: pip install pillow-heif"
        ) from exc

    try:
        heif = pillow_heif.read_heif(str(path))
        rgb = np.asarray(heif.to_pillow().convert("RGB"))
    except Exception as exc:  # noqa: BLE001 - decoder can raise many types
        raise ImageReadError(f"Could not decode HEIC/HEIF image: {path} ({exc})") from exc

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def normalize_image(image: np.ndarray) -> BGRImage:
    """Normalise an arbitrary image array to a 3-channel BGR ``uint8`` image.

    Accepts grayscale (2D), BGR (HxWx3) and BGRA (HxWx4) arrays. The input
    array is never mutated.

    Raises
    ------
    InvalidImageError
        If the array is empty or has invalid dimensions.
    UnsupportedImageFormatError
        If the dtype or channel layout is unsupported.
    """
    if not isinstance(image, np.ndarray):
        raise InvalidImageError(f"Expected a numpy.ndarray, got {type(image).__name__}.")

    if image.size == 0:
        raise InvalidImageError("Image array is empty.")

    if image.ndim not in (2, 3):
        raise InvalidImageError(
            f"Image must have 2 or 3 dimensions, got {image.ndim} dimensions "
            f"with shape {image.shape}."
        )

    if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
        raise UnsupportedImageFormatError(
            f"Unsupported channel count: {image.shape[2]} (expected 1, 3 or 4)."
        )

    if 0 in image.shape[:2]:
        raise InvalidImageError(f"Image has a zero-sized dimension: {image.shape}.")

    working = _to_uint8(image)

    # Collapse a trailing singleton channel to grayscale for uniform handling.
    if working.ndim == 3 and working.shape[2] == 1:
        working = working[:, :, 0]

    if working.ndim == 2:
        bgr = cv2.cvtColor(working, cv2.COLOR_GRAY2BGR)
    elif working.shape[2] == 4:
        bgr = cv2.cvtColor(working, cv2.COLOR_BGRA2BGR)
    else:  # already 3-channel BGR
        bgr = working

    # Guarantee a fresh, contiguous array so callers cannot mutate the input.
    return np.ascontiguousarray(bgr, dtype=np.uint8)


def _to_uint8(image: np.ndarray) -> np.ndarray:
    """Return a ``uint8`` copy of ``image``, scaling float/uint16 inputs."""
    if image.dtype == np.uint8:
        return image.copy()

    if image.dtype == np.uint16:
        scaled = (image.astype(np.float64) / 257.0).round()
        return np.clip(scaled, 0, _MAX_UINT8).astype(np.uint8)

    if np.issubdtype(image.dtype, np.floating):
        finite = image[np.isfinite(image)]
        max_val = float(finite.max()) if finite.size else 0.0
        # Images normalised to [0, 1] are common; scale those up.
        scaled = image * _MAX_UINT8 if max_val <= 1.0 else image
        return np.clip(np.nan_to_num(scaled), 0, _MAX_UINT8).astype(np.uint8)

    if np.issubdtype(image.dtype, np.integer):
        return np.clip(image, 0, _MAX_UINT8).astype(np.uint8)

    raise UnsupportedImageFormatError(
        f"Unsupported image dtype: {image.dtype}. Expected uint8, uint16, "
        "an integer type, or a floating-point type."
    )


def to_grayscale(image: BGRImage) -> np.ndarray:
    """Convert a normalised BGR image to a single-channel grayscale image."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def downscale_longest_side(image: np.ndarray, longest_side: int) -> np.ndarray:
    """Downscale ``image`` so its longest side is at most ``longest_side``.

    Detail-based checks (blur, noise, frequency analysis) are sensitive to
    absolute pixel resolution: the same scene photographed at 12 MP and at
    1 MP produces very different raw sharpness numbers. Measuring at a common
    working resolution makes those signals comparable across devices and also
    keeps processing fast. Images already within the limit are returned
    unchanged. Upscaling is never performed.
    """
    if longest_side <= 0:
        return image
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= longest_side:
        return image
    scale = longest_side / float(longest)
    new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
