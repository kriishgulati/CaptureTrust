# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-11-03

### Fixed
- Added explicit `Pillow>=10.0` to package dependencies in `pyproject.toml`.
- Added `pythonpath = ["src"]` to pytest configuration in `pyproject.toml` so tests can be run directly with `pytest` without needing manual `PYTHONPATH` exports.
- Updated repository, documentation, issues, changelog, and security contact links to `https://github.com/kriishgulati/capturetrust`.

## [1.0.0] - 2026-07-09

Initial public release.

CaptureTrust inspects an image and reports whether it's good enough to use —
checking blur, resolution, lighting, glare, shadow, noise, and (for documents)
whether the frame is cut off — then returns a plain-English score, an
accept/reject decision, and specific reasons and recommendations. It never
claims a photo is fake or fraudulent, only that the quality is or isn't
sufficient.

### Included in this release

- Blur detection (Laplacian variance, motion-blur directionality, edge
  crispness for soft-edged blur)
- Lighting/exposure, glare, shadow, and noise detection
- Document framing check
- Experimental screen-recapture detection (off by default)
- HEIC/HEIF support alongside JPEG/PNG/WebP/BMP/TIFF
- EXIF-aware image loading (photos are always measured in their correct,
  upright orientation)
- Three presets: `CaptureTrustConfig.for_documents()`, `.for_photos()`,
  `.balanced()`
- `inspect_image()`, `inspect_array()`, `inspect_batch()` entry points
- CLI (`capturetrust inspect`, `capturetrust batch`)
- Full type-checked, linted test suite

### Known limitations (documented honestly, not hidden)

- A blurry subject in front of a genuinely sharp background (or the reverse)
  cannot be reliably separated using pixel measurements alone. Three
  approaches were evaluated (Haar cascades, classical saliency, a trained SSD
  face detector) and none solved this without adding significant cost; see
  `docs/limitations.md`.
- Glare detection is calibrated against confirmed-good photos, not against
  confirmed-bad-glare examples, since none were available during development.
- Optional subject detection (face/document region focusing) ships available
  but off by default — measured against a labelled photo set, it did not
  improve accuracy over the default centre-region approach.

### Development history

This release consolidates iterative development and calibration work
(internal versions 0.1.0 through 0.4.0), preserved below for anyone
interested in the reasoning behind specific thresholds and design decisions.

## [0.4.0] - 2026-07-09 (development)


### Fixed (significant)

- **EXIF orientation was not being applied.** Phone cameras often store a
  photo's raw sensor pixels in one orientation with a separate rotation tag
  saying how to display it upright. The loader was decoding raw pixels and
  ignoring that tag, so a portrait photo could be measured as if it were
  landscape (or vice versa) - the "subject region" every check focuses on
  would then no longer line up with where the subject actually is. All image
  loading now goes through Pillow with `exif_transpose` applied, so images are
  always measured in their correct, upright orientation. Discovered because
  `inspect_image()` (file path) and `inspect_array()` (pre-loaded array) could
  give different scores for what was visually the same photo, depending on
  whether the caller's own loader had already corrected the rotation.
  On the labelled photo set, this fixed a photo that was being scored as
  "blurry" (score 76) when it was actually just soft (score 92, correctly
  reclassified) - measured on the wrong orientation, its true subject region
  was never actually being analysed.

## [0.3.2] - 2026-07-09

### Fixed

- **Glare threshold was too strict for ordinary bright photos.** The default
  (10% of the frame bright + low-saturation) was set without real calibration
  data. Measured against 60 labelled good photos, legitimate outdoor daylight
  and document photos (white paper, pale pavement, overcast sky) reached up to
  34% - more than 3x the old threshold - and were being wrongly rejected.
  Raised to 20%, which is validated to fix these false positives with zero
  regression on blurry-photo detection (tested on 89 labelled photos: good
  photos accepted rose, blurry-photo rejection unchanged).

### Note

- Unlike blur, glare has never been calibrated against genuine bad-glare
  examples - the new default is a defensible correction based on what good
  photos actually look like, not a proven boundary for when glare is truly
  excessive. If precise glare calibration matters for your use case, provide
  labelled examples of unusable glare-affected photos.

## [0.3.1] - 2026-07-08

### Improved

- **Added an edge-crispness blur signal.** Soft edges are a blur signature even
  when an image is full of texture (motion-blurred grass or foliage keeps a high
  Laplacian variance but its edges are soft). This catches textured motion blur
  the variance-based measure missed, lifting blurry-photo detection to 28/29 on
  the labelled set with no new false positives on good photos. The crispness
  floor scales with the configured sharp boundary, so the lenient ``for_photos``
  preset still accepts genuinely sharp but smooth/bokeh subjects.

### Still not solvable without subject detection

- A blurry subject in front of a genuinely sharp background still passes,
  because part of the frame really is sharp. Distinguishing this from a sharp
  subject with a blurred background (bokeh) requires knowing which region is the
  intended subject - a DNN-scale problem, not a threshold.

## [0.3.0] - 2026-07-08

### Added

- **Configuration presets** for common contexts, since one blur threshold
  cannot serve both strict document scanning and lenient artistic photography
  (a sharp subject with a blurred background and a blurry subject with a sharp
  background are near-indistinguishable from pixels alone):
  - `CaptureTrustConfig.for_documents()` - strict; requires genuinely sharp,
    well-framed pages suitable for OCR.
  - `CaptureTrustConfig.for_photos()` - lenient; accepts smooth subjects and
    shallow depth-of-field (bokeh) while still rejecting clearly blurry photos.
  - `CaptureTrustConfig.balanced()` - general-purpose defaults.
  All presets accept keyword overrides.

## [0.2.0] - 2026-07-08

### Added

- **HEIC/HEIF support.** iPhone photos (.heic/.heif) are now read directly via
  pillow-heif, which is now a dependency. Previously these files could not be
  opened at all.
- **Subject detection (faces and documents), opt-in.** When enabled
  (`enable_subject_detection=True`), the blur check focuses on a detected face
  or document instead of the centre region. It is **off by default**: measured
  against a labelled photo set it did not improve accept/reject accuracy (the
  bundled Haar face detector is unreliable on close-up/tilted faces, a
  heavily-blurred face cannot be detected at all, and a mistaken detection can
  flip a blurry photo to acceptable). It falls back safely to centre-region
  analysis when no confident subject is found. Reported via the
  `subject_detected` / `subject_type` metrics.

### Note

- Subject detection was shipped off-by-default deliberately, following the same
  evidence-based approach as blur calibration: a feature is only made default
  once it demonstrably improves measured accuracy. A robust version would need
  a DNN face detector (extra model weight), which is deferred to keep the
  library lightweight.

## [0.1.5] - 2026-07-08

### Fixed

- **A photo the blur check rates medium/high is no longer marked acceptable**,
  even if its numeric score clears the threshold. Previously a blurry photo
  could pass a quality gate simply because its score landed above the pass
  mark. Controlled by the new `reject_blurry` config option (default True).
- **Added a directionality (motion-blur) signal.** Motion blur concentrates
  gradient energy along one axis; when the centre is strongly directional the
  blur severity is bumped up, catching textured motion blur (foliage, grass)
  that keeps a deceptively high Laplacian variance. The threshold sits above
  the range seen in sharp photos, so crisp images are unaffected.

### Added

- `directionality` reported in the blur metrics.
- `reject_blurry` option on `CaptureTrustConfig`.

### Still hard

- A blurry subject in front of a genuinely sharp background can still pass,
  because the sharp region is not directional and keeps the centre sharpness
  high. This needs subject/face detection (roadmap).

## [0.1.4] - 2026-07-06

### Fixed

- **Blur detection recalibrated against a labelled set of ~60 real photos.**
  The sharp/blurry boundary was far too lenient (tuned earlier on a couple of
  unusually soft selfies), so most genuinely blurry photos were passing. The
  decision now uses the centre-region Laplacian variance with a data-driven
  boundary, lifting blur agreement with human labels from ~69% to ~90-95% while
  still catching every blurry photo in the set.
- Fixed a native crash (heap corruption in OpenCV) that could occur when the
  centre-region was analysed as a non-contiguous array view.

### Note

- Two classes of blurry photo remain genuinely hard and may be under-flagged: a
  blurry subject in front of a sharp background, and heavily textured motion
  blur (e.g. grass/foliage) whose streaks read as detail. Robustly handling
  these needs subject/face detection (roadmap). Thresholds remain provisional
  and calibrated on a modest sample; see docs/limitations.

## [0.1.3] - 2026-07-05

### Changed

- The experimental **screen-recapture check is now OFF by default**. On a wide
  range of real photos it produced false positives (ornate objects, textures
  and printed patterns trip it) and it cannot be calibrated reliably without a
  labelled set of genuine screen recaptures. Enable it explicitly via
  `CaptureTrustConfig(enable_screen_recapture_check=True)` or the CLI
  `--enable-screen-check` flag.
- Orientation detection is far more conservative: everyday handheld tilt is no
  longer reported; only clear skew (>= 10 degrees) is surfaced. It remains
  report-only and never affects the score.
- Noise thresholds raised so fine legitimate detail (hair, fabric, jewellery,
  foliage) is no longer mistaken for sensor noise.

### CLI

- Replaced `--disable-screen-check` with `--enable-screen-check` (the check is
  now off by default).

## [0.1.2] - 2026-07-05

### Fixed

- Blur detection is now weighted toward the centre of the frame, where the
  subject usually sits. A whole-frame measurement was being fooled by busy,
  detailed backgrounds: a photo with a blurry face but a cluttered background
  could score as sharp. Centre-weighting makes the score track what a person
  actually perceives, widening the gap between clearly-sharp and clearly-blurry
  images.

### Changed

- Blur metrics reported are now `center_laplacian_variance` and
  `center_edge_density` (the whole-frame `blur_score` is still included).

## [0.1.1] - 2026-07-05

### Fixed

- Blur is now measured at a normalised working resolution, so large phone
  photos are no longer judged as blurry purely because of their pixel count.
  Blur severity is graded, so slightly-soft and genuinely-blurry images are
  scored differently.
- Shadow detection no longer flags ordinary dark backgrounds, hair, or
  clothing as "heavy shadows".
- The experimental screen-recapture heuristic now requires moiré corroboration
  before raising a medium/high risk, removing false positives on normal photos.
- Faster inspection (typically well under a second) thanks to working-resolution
  processing.

### Changed

- High-severity blur now deducts more, so a clearly blurry image is reported as
  not acceptable rather than borderline.
- Added `working_resolution` to `CaptureTrustConfig`.
- Added an `evaluate_folder` example for plain-language batch checking.

## [0.1.0] - 2026-07-05

### Added

- Initial public release.
- Core API: `inspect_image`, `inspect_array`, `inspect_batch`.
- `CaptureTrustConfig` dataclass with full `__post_init__` validation.
- `CaptureTrustReport` dataclass with `to_dict`, `to_json`, and `summary`.
- Image checks: blur, resolution/aspect ratio, lighting/exposure, glare,
  noise, shadows, orientation, document framing, and an experimental
  screen-recapture heuristic.
- Explainable, deterministic weighted scoring engine with traceable
  per-check deductions.
- Detail-based checks are measured at a configurable working resolution
  (`working_resolution`, default 1024) so sharpness and noise are comparable
  across camera resolutions; the resolution check still reports true
  dimensions. This also keeps typical inspections well under a second.
- Blur severity is graded (soft vs blurry) and calibrated against real phone
  photos; the shadow and experimental screen-recapture heuristics are tuned to
  avoid false positives on ordinary photos (the latter now requires moiré
  corroboration). Default thresholds are provisional — see docs/limitations.
- Deduplicated recommendations engine with careful, non-accusatory wording.
- `capturetrust` command-line interface with `inspect` and `batch`
  subcommands, JSON and human-readable output, and standard exit codes.
- Custom exception hierarchy.
- Test suite built on synthetic NumPy images.
- Documentation: architecture, scoring, and limitations.
- Packaging with `pyproject.toml` (src layout, typed marker, console script).
- GitHub Actions workflows for tests, linting/typing, and manual publishing.

[Unreleased]: https://github.com/your-org/capturetrust/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/capturetrust/releases/tag/v1.0.0

<!-- Internal development tags (pre-1.0, not separately published): -->
[0.4.0]: https://github.com/your-org/capturetrust/releases/tag/v0.4.0
[0.3.2]: https://github.com/your-org/capturetrust/releases/tag/v0.3.2
[0.3.1]: https://github.com/your-org/capturetrust/releases/tag/v0.3.1
[0.3.0]: https://github.com/your-org/capturetrust/releases/tag/v0.3.0
[0.2.0]: https://github.com/your-org/capturetrust/releases/tag/v0.2.0
[0.1.5]: https://github.com/your-org/capturetrust/releases/tag/v0.1.5
[0.1.4]: https://github.com/your-org/capturetrust/releases/tag/v0.1.4
[0.1.3]: https://github.com/your-org/capturetrust/releases/tag/v0.1.3
[0.1.2]: https://github.com/your-org/capturetrust/releases/tag/v0.1.2
[0.1.1]: https://github.com/your-org/capturetrust/releases/tag/v0.1.1
[0.1.0]: https://github.com/your-org/capturetrust/releases/tag/v0.1.0
