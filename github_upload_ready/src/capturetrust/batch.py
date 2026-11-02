"""Batch inspection helpers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .api import inspect_image
from .config import CaptureTrustConfig
from .report import CaptureTrustReport

__all__ = ["inspect_batch"]


def inspect_batch(
    image_paths: list[str | Path],
    *,
    config: CaptureTrustConfig | None = None,
    workers: int = 1,
) -> list[CaptureTrustReport]:
    """Inspect several images and return reports in input order.

    Parameters
    ----------
    image_paths:
        Ordered list of image file paths.
    config:
        Optional shared configuration.
    workers:
        Number of worker threads. Concurrency is only used when > 1.

    Notes
    -----
    Output order always matches input order regardless of ``workers``. If an
    individual image raises during inspection, the exception propagates - use
    the CLI ``batch`` command (or wrap calls yourself) if you need per-file
    error isolation.
    """
    if workers < 1:
        raise ValueError(f"workers must be >= 1 (got {workers}).")

    config = config or CaptureTrustConfig()

    if workers == 1 or len(image_paths) <= 1:
        return [inspect_image(path, config=config) for path in image_paths]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # executor.map preserves input ordering.
        results = list(executor.map(lambda p: inspect_image(p, config=config), image_paths))
    return results
