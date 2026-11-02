# CaptureTrust

**One clean package and one explainable report that answer a single question about an image: is it good enough to accept, and if not, what should the person do to fix it?**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/kriishgulati/capturetrust/actions/workflows/tests.yml/badge.svg)](https://github.com/kriishgulati/capturetrust/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/capturetrust.svg)](https://pypi.org/project/capturetrust/)

CaptureTrust inspects an uploaded image and estimates whether it is *visually*
suitable for downstream workflows — OCR, document scanning, form uploads,
receipts and invoices, marketplace listings, KYC pre-checks, and general photo
quality validation — then returns an explainable, actionable report.

---

## Features

- **Blur detection** — variance of Laplacian, Tenengrad focus, and edge density
  blended into an explainable severity, not a single magic number.
- **Resolution & aspect ratio** — dimensions, megapixels, and unusual-ratio
  labelling against configurable minimums.
- **Lighting & exposure** — brightness statistics, under/over-exposure, dynamic
  range, and uneven-lighting estimation.
- **Glare detection** — HSV high-value / low-saturation regions cleaned with
  morphology and ranked by area.
- **Noise estimation** — a conservative high-frequency residual heuristic that
  avoids confusing natural texture with sensor noise.
- **Shadow estimation** — best-effort illumination-shadow coverage in LAB space.
- **Orientation** — conservative dominant-line rotation estimate (report only).
- **Document framing** — best-effort quadrilateral detection with candidate
  scoring, corner visibility, tilt, perspective and framing quality.
- **Experimental screen-recapture heuristic** (opt-in, **off by default**) —
  combines several weak visual signals into a labelled risk. **Never** a fraud
  verdict, and prone to false positives, so you must enable it deliberately.
- **Explainable scoring** — deterministic, fully traceable per-check deductions.
- **Friendly recommendations** — specific, deduplicated, non-accusatory advice.
- **CLI + batch** — inspect single files or whole folders, human or JSON output.

## Why CaptureTrust exists

Teams that accept user-uploaded images usually end up stitching together a pile
of one-off OpenCV scripts for blur, lighting, glare, framing, and so on — each
with its own thresholds and no shared explanation. CaptureTrust replaces that
with one lightweight, GPU-free package and one report that says *why* an image
might not be usable and *what to do about it*. It is intuitive for beginners and
architected for contributors and production use.

CaptureTrust never claims an image is "fake", "fraudulent", "tampered", or
"invalid". It produces a visual **quality estimate**, not a fraud decision.

## Installation

```bash
pip install capturetrust
```

CaptureTrust is lightweight and GPU-free. It depends only on `numpy` and
`opencv-python-headless`, and runs on Linux, Windows, macOS, Docker, and
headless cloud environments.

## Quickstart

```python
from capturetrust import inspect_image

report = inspect_image("photo.jpg")

print(report.summary())
print(report.to_dict())
```

### Google Colab

```python
!pip install capturetrust

from google.colab import files
from capturetrust import inspect_image

uploaded = files.upload()
filename = next(iter(uploaded))

report = inspect_image(filename)

print(report.to_json())
```

### Jupyter Notebook

```python
!pip install capturetrust

from capturetrust import inspect_image

report = inspect_image("scan.png")
report.to_dict()
```

### Local Python script

```python
from capturetrust import inspect_image, CaptureTrustConfig

config = CaptureTrustConfig(min_width=1024, min_height=768, acceptable_score=75)
report = inspect_image("id_card.jpg", config=config)

if not report.is_acceptable:
    for issue, tip in zip(report.issues, report.recommendations):
        print(f"- {issue}: {tip}")
```

### Inspecting a NumPy array

```python
import cv2
from capturetrust import inspect_array

image = cv2.imread("photo.jpg")          # BGR, grayscale, or RGBA all accepted
report = inspect_array(image)
print(report.score, report.is_acceptable)
```

## Command-line interface

```bash
capturetrust inspect image.jpg
capturetrust inspect image.jpg --json
capturetrust inspect image.jpg --pretty
capturetrust inspect image.jpg --min-width 1024 --min-height 768
capturetrust inspect image.jpg --disable-document-check
capturetrust inspect image.jpg --enable-screen-check   # opt in to experimental check

capturetrust batch ./images
capturetrust batch ./images --json-output results.json --workers 4

capturetrust --version
```

Exit codes: `0` acceptable, `1` not acceptable, `2` processing error,
`3` usage error.

## Batch processing

```python
from capturetrust import inspect_batch

paths = ["a.jpg", "b.png", "c.webp"]
reports = inspect_batch(paths, workers=4)   # output order matches input order

for path, report in zip(paths, reports):
    print(path, report.score, report.is_acceptable)
```

## Example report

```json
{
  "score": 65,
  "is_acceptable": false,
  "confidence": "medium",
  "issues": [
    "Image is blurry",
    "Heavy shadows detected"
  ],
  "recommendations": [
    "Retake the image while holding the camera steady and ensuring the subject is in focus.",
    "Reposition the light source or subject to avoid strong shadows."
  ],
  "warnings": [
    "Screen recapture analysis is experimental and should not be treated as proof."
  ],
  "metrics": {
    "width": 640,
    "height": 480,
    "blur_score": 42.8,
    "average_brightness": 79.5,
    "glare_ratio": 0.0,
    "noise_score": 0.02,
    "shadow_ratio": 0.17,
    "document_detected": false,
    "screen_recapture_score": 0.0,
    "screen_recapture_risk": "low"
  },
  "checks": {
    "blur": { "enabled": true, "passed": false, "severity": "high" },
    "shadow": { "enabled": true, "passed": false, "severity": "medium" }
  },
  "metadata": {
    "library_version": "0.1.0",
    "image_source_type": "numpy_array",
    "processing_time_ms": 12.4
  }
}
```

## Presets

Image quality is context-dependent: a document scan must be genuinely sharp for
OCR, while an artistic photo with a deliberately blurred background (bokeh)
should pass. No single threshold serves both, so choose the preset that matches
your content:

```python
from capturetrust import inspect_image, CaptureTrustConfig

# Strict - documents, receipts, ID cards (must be sharp and well framed)
report = inspect_image("scan.jpg", config=CaptureTrustConfig.for_documents())

# Lenient - general and artistic photography (accepts smooth subjects, bokeh)
report = inspect_image("portrait.jpg", config=CaptureTrustConfig.for_photos())

# General purpose (the default)
report = inspect_image("photo.jpg", config=CaptureTrustConfig.balanced())
```

Any preset accepts overrides, e.g. `CaptureTrustConfig.for_photos(acceptable_score=50)`.

## Configuration

Every threshold is adjustable without editing library code:

```python
from capturetrust import CaptureTrustConfig, inspect_image

config = CaptureTrustConfig(
    min_width=1024,
    min_height=768,
    acceptable_score=75,
    blur_threshold=110.0,
    glare_threshold=0.12,
    enable_document_check=True,
    enable_screen_recapture_check=True,
)

report = inspect_image("photo.jpg", config=config)
```

All fields are validated in `__post_init__`: dimensions must be positive,
scores must be within 0–100, ratios within 0–1, brightness thresholds must be
ordered sensibly, and the screen-recapture medium threshold must be below the
high threshold.

## Explainable scoring

Scoring starts at 100 and applies traceable deductions by check and severity.
The full explanation is included in the report under
`metrics.score_explanation`:

```json
{
  "starting_score": 100,
  "adjustments": [
    { "check": "blur", "severity": "high", "deduction": 40, "reason": "Low focus sharpness detected" },
    { "check": "glare", "severity": "medium", "deduction": 15, "reason": "Large bright low-saturation regions detected" }
  ],
  "final_score": 55
}
```

Scores are deterministic for the same input and config, always clamped to
0–100, and never heavily penalise document framing when no document is present.
See [docs/scoring.md](docs/scoring.md) for the full deduction table and how to
override it.

## Supported file formats

`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff` / `.tif`, and `.heic` / `.heif` (iPhone photos).

Array inputs may be OpenCV BGR, single-channel grayscale, or RGBA; they are
normalised internally to BGR without mutating the caller's array.

## Performance expectations

CaptureTrust is CPU-only and typically inspects a normal-sized photo in tens of
milliseconds on commodity hardware. Very large images cost more; downscaling
before inspection is a reasonable optimisation for high-throughput pipelines.
Batch mode can use a thread pool via the `workers` argument.

## Ethical limitations

CaptureTrust estimates **visual quality only**. It is **not** an anti-fraud,
tamper-detection, or identity-verification system. Do not use its output as the
sole basis for legal, financial, employment, academic, insurance, or identity
decisions. High-impact contexts require human review. See
[docs/limitations.md](docs/limitations.md).

## False positive warning

Heuristics can misfire. Fabrics, printed pages, brick walls, mesh, halftone
print, heavy compression, and genuinely patterned subjects can trigger noise,
shadow, or screen-recapture signals even when the image is perfectly fine.
Treat every signal as a *possibility to review*, not a conclusion.

## Screen-recapture warning

The screen-recapture check is **experimental**. It looks for visual
characteristics sometimes associated with photographing a phone, tablet, or
monitor (frequency peaks, moiré-like energy, repeating line patterns,
reflection cues). It can produce both false positives and false negatives and
**must never be treated as proof of recapture or fraud.** Every report that
runs this check includes an explicit warning to that effect.

## Security and privacy

- Images are processed **locally** in your own Python environment and are **not
  uploaded anywhere** by this library.
- No network calls, no telemetry, no data collection.
- No temporary files or logs of image content during normal operation.
- Malformed images are handled as safely as practical via typed exceptions.

See [SECURITY.md](SECURITY.md).

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and
our [Code of Conduct](CODE_OF_CONDUCT.md). The quality gate is:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## What's included in 1.0.0

- Blur, resolution, lighting, glare, shadow, and noise detection
- Document framing check (are all four corners visible)
- Experimental screen-recapture detection (off by default)
- HEIC/HEIF support (iPhone photos), alongside JPEG/PNG/WebP/BMP/TIFF
- Three ready-made presets: `for_documents()`, `for_photos()`, `balanced()`
- EXIF-aware image loading (photos are always measured in their correct
  upright orientation)
- CLI (`capturetrust inspect`, `capturetrust batch`)
- Batch processing with optional multithreading
- Full test suite, type-checked, linted

## Known limitations

- A blurry subject in front of a genuinely sharp background (or the reverse)
  cannot be reliably told apart from pixels alone. See
  [`docs/limitations.md`](docs/limitations.md) for the full explanation.
- Glare detection is calibrated against good photos, not against confirmed
  bad-glare examples - if precise glare tuning matters for your use case,
  provide labelled examples.
- Optional subject detection (face/document region focusing) is available
  but off by default: measured against a labelled photo set, it did not
  improve accuracy over the default centre-region approach.

## Roadmap

Future direction depends on real-world feedback from this release. Candidates
under consideration: a trained subject-detection model to address the known
blurry-subject limitation, broader glare calibration against real bad-glare
examples, and expanded format/locale testing.

## License

Released under the [MIT License](LICENSE).
