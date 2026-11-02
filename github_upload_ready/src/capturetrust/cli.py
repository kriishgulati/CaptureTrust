"""Command-line interface for CaptureTrust (argparse only)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .api import inspect_image
from .config import CaptureTrustConfig
from .exceptions import CaptureTrustError
from .utils import SUPPORTED_SUFFIXES
from .version import __version__

__all__ = ["main", "build_parser"]

_EXIT_OK = 0
_EXIT_NOT_ACCEPTABLE = 1
_EXIT_ERROR = 2
_EXIT_USAGE = 3


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="capturetrust",
        description=(
            "Estimate whether an image is visually suitable for downstream "
            "workflows (OCR, document scanning, uploads, and so on). Results "
            "are visual quality estimates, not fraud decisions."
        ),
    )
    parser.add_argument("--version", action="version", version=f"capturetrust {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect
    inspect_p = subparsers.add_parser("inspect", help="Inspect a single image.")
    inspect_p.add_argument("image", help="Path to the image file.")
    inspect_p.add_argument("--json", action="store_true", help="Emit a compact JSON report.")
    inspect_p.add_argument("--pretty", action="store_true", help="Emit an indented JSON report.")
    _add_config_arguments(inspect_p)
    inspect_p.set_defaults(func=_cmd_inspect)

    # batch
    batch_p = subparsers.add_parser("batch", help="Inspect every image in a directory.")
    batch_p.add_argument("directory", help="Directory containing images.")
    batch_p.add_argument(
        "--json-output",
        metavar="PATH",
        help="Write the full batch result as JSON to this file.",
    )
    batch_p.add_argument(
        "--workers", type=int, default=1, help="Number of worker threads (default: 1)."
    )
    _add_config_arguments(batch_p)
    batch_p.set_defaults(func=_cmd_batch)

    return parser


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-width", type=int, help="Minimum acceptable width in pixels.")
    parser.add_argument("--min-height", type=int, help="Minimum acceptable height in pixels.")
    parser.add_argument(
        "--acceptable-score", type=int, help="Score (0-100) required to be acceptable."
    )
    parser.add_argument(
        "--disable-document-check",
        action="store_true",
        help="Skip document detection and framing checks.",
    )
    parser.add_argument(
        "--enable-screen-check",
        action="store_true",
        help="Enable the experimental screen-recapture check (off by default; "
        "high false-positive rate on ordinary photos).",
    )


def _config_from_args(args: argparse.Namespace) -> CaptureTrustConfig:
    kwargs: dict = {}
    if getattr(args, "min_width", None) is not None:
        kwargs["min_width"] = args.min_width
    if getattr(args, "min_height", None) is not None:
        kwargs["min_height"] = args.min_height
    if getattr(args, "acceptable_score", None) is not None:
        kwargs["acceptable_score"] = args.acceptable_score
    if getattr(args, "disable_document_check", False):
        kwargs["enable_document_check"] = False
    if getattr(args, "enable_screen_check", False):
        kwargs["enable_screen_recapture_check"] = True
    return CaptureTrustConfig(**kwargs)


def _cmd_inspect(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    try:
        report = inspect_image(args.image, config=config)
    except CaptureTrustError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return _EXIT_ERROR

    if args.json or args.pretty:
        print(report.to_json(indent=2 if args.pretty else 0))
    else:
        print(_human_report(args.image, report))

    return _EXIT_OK if report.is_acceptable else _EXIT_NOT_ACCEPTABLE


def _human_report(name: str, report) -> str:  # type: ignore[no-untyped-def]
    decision = "ACCEPTABLE" if report.is_acceptable else "NEEDS REVIEW"
    lines = [
        f"File: {name}",
        f"Score: {report.score}/100   Decision: {decision}   Confidence: {report.confidence}",
    ]
    if report.issues:
        lines.append("Issues:")
        lines.extend(f"  - {i}" for i in report.issues)
    if report.recommendations:
        lines.append("Recommendations:")
        lines.extend(f"  - {r}" for r in report.recommendations)
    selected = {
        k: report.metrics.get(k)
        for k in ("width", "height", "blur_score", "average_brightness", "glare_ratio")
        if k in report.metrics
    }
    if selected:
        lines.append("Metrics:")
        lines.extend(f"  {k}: {v}" for k, v in selected.items())
    if report.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in report.warnings)
    return "\n".join(lines)


def _cmd_batch(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"Error: not a directory: {directory}", file=sys.stderr)
        return _EXIT_ERROR

    config = _config_from_args(args)
    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)

    results: list[dict] = []
    skipped: list[dict] = []

    for path in files:
        try:
            report = inspect_image(path, config=config)
        except CaptureTrustError as exc:
            skipped.append({"file": str(path), "error": str(exc)})
            continue
        results.append({"file": str(path), "report": report.to_dict()})

    payload = {"results": results, "skipped": skipped, "total": len(files)}

    if args.json_output:
        Path(args.json_output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(results)} reports to {args.json_output} ({len(skipped)} skipped).")
    else:
        for item in results:
            report_dict = item["report"]
            decision = "ACCEPTABLE" if report_dict["is_acceptable"] else "NEEDS REVIEW"
            print(f"{item['file']}: {report_dict['score']}/100  {decision}")
        for item in skipped:
            print(f"{item['file']}: SKIPPED ({item['error']})", file=sys.stderr)

    return _EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:  # pragma: no cover - argparse enforces required subcommand
        parser.print_help()
        return _EXIT_USAGE
    try:
        return int(func(args))
    except BrokenPipeError:  # pragma: no cover - occurs with piped output (e.g. | head)
        # Downstream closed the pipe; exit quietly without a traceback.
        sys.stdout.close()
        return _EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
