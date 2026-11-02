"""Customise thresholds and deductions with CaptureTrustConfig."""

from __future__ import annotations

import sys

from capturetrust import CaptureTrustConfig, inspect_image


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python examples/custom_config.py <image_path>")
        return 2

    config = CaptureTrustConfig(
        min_width=1024,
        min_height=768,
        acceptable_score=75,
        blur_threshold=110.0,
        glare_threshold=0.12,
        enable_document_check=True,
        enable_screen_recapture_check=True,
        # Make a high-severity blur cost more than the default 30 points.
        deduction_overrides={"blur": {"high": 40}},
    )

    report = inspect_image(sys.argv[1], config=config)

    print(report.summary())
    for issue, tip in zip(report.issues, report.recommendations):
        print(f"- {issue} -> {tip}")

    return 0 if report.is_acceptable else 1


if __name__ == "__main__":
    raise SystemExit(main())
