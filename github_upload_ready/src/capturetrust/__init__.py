"""CaptureTrust: explainable image quality inspection for downstream workflows.

CaptureTrust answers one question about an uploaded image: *"Is this good
enough to accept, and if not, what should the person do to fix it?"* It bundles
blur, resolution, lighting, glare, noise, shadow, orientation, document-framing
and (experimental) screen-recapture checks behind one clean, explainable report.

Example
-------
>>> from capturetrust import inspect_image
>>> report = inspect_image("photo.jpg")  # doctest: +SKIP
>>> report.to_dict()                       # doctest: +SKIP
"""

from __future__ import annotations

from .api import inspect_array, inspect_image
from .batch import inspect_batch
from .config import CaptureTrustConfig
from .exceptions import (
    CaptureTrustError,
    ImageReadError,
    InvalidConfigurationError,
    InvalidImageError,
    UnsupportedImageFormatError,
)
from .report import CaptureTrustReport
from .version import __version__

__all__ = [
    "inspect_image",
    "inspect_array",
    "inspect_batch",
    "CaptureTrustReport",
    "CaptureTrustConfig",
    "CaptureTrustError",
    "InvalidImageError",
    "UnsupportedImageFormatError",
    "ImageReadError",
    "InvalidConfigurationError",
    "__version__",
]
