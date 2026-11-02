"""The :class:`CaptureTrustReport` result object."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .types import Confidence

__all__ = ["CaptureTrustReport"]


@dataclass
class CaptureTrustReport:
    """Structured result of inspecting a single image.

    The report is intentionally a plain data object: it carries the score, a
    human-friendly acceptance decision, the detected issues with matching
    recommendations, and the full metrics/checks/metadata needed to audit how
    the score was reached.
    """

    score: int
    is_acceptable: bool
    confidence: Confidence
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a JSON-serialisable dictionary."""
        return {
            "score": self.score,
            "is_acceptable": self.is_acceptable,
            "confidence": self.confidence,
            "issues": list(self.issues),
            "recommendations": list(self.recommendations),
            "warnings": list(self.warnings),
            "metrics": _jsonify(self.metrics),
            "checks": _jsonify(self.checks),
            "metadata": _jsonify(self.metadata),
        }

    def to_json(self, indent: int = 2) -> str:
        """Return the report serialised as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    def summary(self) -> str:
        """Return a short, human-readable multi-line summary."""
        decision = "ACCEPTABLE" if self.is_acceptable else "NEEDS REVIEW"
        lines = [
            f"CaptureTrust score: {self.score}/100  [{decision}]",
            f"Confidence: {self.confidence}",
        ]
        if self.issues:
            lines.append("Issues:")
            lines.extend(f"  - {issue}" for issue in self.issues)
        else:
            lines.append("Issues: none detected")
        if self.recommendations:
            lines.append("Recommendations:")
            lines.extend(f"  - {rec}" for rec in self.recommendations)
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {warning}" for warning in self.warnings)
        lines.append("Note: this result is a visual quality estimate, not a fraud decision.")
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.summary()


def _jsonify(value: Any) -> Any:
    """Recursively coerce numpy scalars/containers into plain Python types."""
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, bool):
        return value
    # numpy scalar types expose .item(); fall back to native types.
    item = getattr(value, "item", None)
    if callable(item) and value.__class__.__module__ == "numpy":
        return value.item()
    return value
