"""Custom exception hierarchy for CaptureTrust.

All exceptions raised intentionally by the library derive from
:class:`CaptureTrustError`, so callers can catch every library-specific
error with a single ``except`` clause.
"""

from __future__ import annotations

__all__ = [
    "CaptureTrustError",
    "InvalidImageError",
    "UnsupportedImageFormatError",
    "ImageReadError",
    "InvalidConfigurationError",
]


class CaptureTrustError(Exception):
    """Base class for all CaptureTrust errors."""


class InvalidImageError(CaptureTrustError):
    """Raised when an image array is structurally invalid.

    Examples include empty arrays, arrays with zero-sized dimensions, or
    arrays whose shape cannot be interpreted as an image.
    """


class UnsupportedImageFormatError(InvalidImageError):
    """Raised when an image has an unsupported dtype or channel layout."""


class ImageReadError(CaptureTrustError):
    """Raised when an image file cannot be found, opened, or decoded."""


class InvalidConfigurationError(CaptureTrustError):
    """Raised when a :class:`~capturetrust.config.CaptureTrustConfig` is invalid."""
