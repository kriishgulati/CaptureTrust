"""Shared type definitions used across CaptureTrust modules."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "Severity",
    "Confidence",
    "ImageSourceType",
    "BGRImage",
    "CheckResult",
    "Metrics",
]

# A severity label attached to individual checks.
Severity = Literal["none", "low", "medium", "high"]

# Overall confidence of the report.
Confidence = Literal["low", "medium", "high"]

# How the inspected image was provided.
ImageSourceType = Literal["file_path", "numpy_array"]

# Normalised 3-channel BGR uint8 image.
BGRImage = NDArray[np.uint8]

# Structured return value of an individual check.
CheckResult = dict[str, Any]

# Aggregated metrics mapping.
Metrics = dict[str, Any]
