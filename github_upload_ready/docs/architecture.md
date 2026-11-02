# Architecture

This document describes how CaptureTrust is structured and how a request flows
through the library.

## Public API flow

```
inspect_image(path)  ─┐
                      ├─► load & normalise ─► run checks ─► score ─► recommend ─► CaptureTrustReport
inspect_array(array) ─┘
```

1. **Entry points** (`api.py`). `inspect_image` reads a file from disk;
   `inspect_array` accepts an in-memory NumPy array. Both funnel into a single
   internal orchestration routine so behaviour is identical regardless of input
   source. `inspect_batch` (`batch.py`) fans out over many paths, optionally
   using a thread pool, while preserving input order.
2. **Normalisation** (`utils.py`). The input is validated and converted to a
   contiguous BGR `uint8` array. Grayscale, BGR, BGRA, `uint16`, integer, and
   floating-point inputs are all coerced without mutating the caller's array.
   Unsupported dtypes and empty/invalid arrays raise typed exceptions.
3. **Checks.** Each enabled check module is invoked. Every check is wrapped so
   that a single failure records an error and is treated as a non-blocking pass
   rather than crashing the whole inspection.
4. **Scoring** (`scoring.py`). Check severities are converted into deterministic,
   traceable deductions from a starting score of 100.
5. **Recommendations** (`recommendations.py`). Failed checks map to
   deduplicated, friendly issues, recommendations, and warnings.
6. **Report** (`report.py`). Everything is assembled into a `CaptureTrustReport`
   dataclass exposing `to_dict`, `to_json`, and `summary`.

## Image normalisation

Normalisation is deliberately centralised so every check receives the same
canonical format. Key properties:

- Output is always contiguous BGR `uint8`.
- `uint16` is scaled down; floats in `[0, 1]` are scaled up; other integer and
  float ranges are clipped safely; `NaN`/`inf` are neutralised.
- The caller's original array is never modified in place.
- Unicode file paths are handled via `numpy.fromfile` + `cv2.imdecode` so paths
  work consistently across platforms.

## Individual check modules

| Module | Responsibility |
| --- | --- |
| `quality.py` | Blur (Laplacian variance, Tenengrad, edge density) and resolution/aspect ratio. |
| `lighting.py` | Brightness statistics, exposure, dynamic range, uneven lighting. |
| `glare.py` | HSV high-value / low-saturation region detection and ranking. |
| `noise.py` | Conservative high-frequency residual noise estimate. |
| `shadows.py` | LAB-based illumination-shadow coverage estimate. |
| `orientation.py` | Conservative dominant-line rotation estimate (report only). |
| `document.py` | Best-effort quadrilateral detection, framing and perspective. |
| `recapture.py` | Experimental screen-recapture heuristic. |

Each check returns a structured dictionary including at least an outcome and a
`severity` in `{none, low, medium, high}`.

## Scoring engine

The scoring engine (`scoring.py`) holds a default deduction table keyed by check
and severity. It starts at 100, subtracts the relevant deduction for each check
that did not pass, clamps the result to `[0, 100]`, and records every adjustment
with its reason. Deductions can be overridden per config, and disabled checks
contribute nothing.

## Recommendations engine

The recommendations engine (`recommendations.py`) translates check outcomes into
human-friendly text. It guarantees deduplication and uses careful, estimative
wording. When the experimental screen-recapture check runs, it always appends a
warning that the result is not proof.

## CLI architecture

The CLI (`cli.py`) is built on `argparse` with two subcommands, `inspect` and
`batch`. It maps command-line flags onto a `CaptureTrustConfig`, renders either
human-readable or JSON output, and returns standard exit codes so it composes
well in shell pipelines and CI.

## Why checks are heuristic

Image "quality" is context-dependent and cannot be measured exactly from pixels
alone. Every check is therefore a best-effort heuristic tuned to be explainable
and conservative. CaptureTrust favours transparent, adjustable signals over an
opaque model, which is why every deduction is traceable and every threshold is
configurable.
