# Limitations

CaptureTrust is a best-effort **visual quality** estimator. Understanding its
limits is essential to using it responsibly.

## Cameras and lighting environments vary

Sensors, lenses, white balance, compression, and ambient lighting differ
enormously across devices and settings. A threshold that is well-tuned for one
population of images can be too strict or too loose for another. Always
calibrate `CaptureTrustConfig` against a representative sample of your own
images before relying on the defaults.

## Printed patterns and screen-like artefacts

Regular textures — fabric weave, halftone print, brick, mesh, tiled floors,
patterned wallpaper — can resemble the frequency signatures the library
associates with noise or screen recapture. Compression artefacts can do the
same. These are genuine sources of confusion, not bugs.

## False positives (and false negatives)

Every check can misfire in both directions. A perfectly good image can trigger a
signal, and a poor image can slip through. This is inherent to pixel-only
heuristics. Treat each signal as *a possibility to review*, never a verdict.

The **screen-recapture** check is explicitly experimental and the most prone to
error. It must never be treated as proof that an image was photographed from a
display, and never as evidence of fraud.

## No fraud-detection guarantee

CaptureTrust does not detect tampering, deepfakes, editing, forgery, or identity
mismatch. It has no notion of whether an image is authentic. It only estimates
whether an image is *visually clear enough* to process.

## Not a standalone decision system

CaptureTrust must not be the only system making decisions in **legal**,
**financial**, **employment**, **academic**, **insurance**, or
**identity-verification** contexts. Its output is a quality signal to support a
workflow, not to replace human judgement.

## Human review in high-impact contexts

Wherever an incorrect accept/reject decision could materially harm a person —
denying a claim, rejecting an application, flagging an identity document — a
human must review the case. Use CaptureTrust to prioritise and explain, not to
adjudicate.

## Version 0.1.0 specifics

- Detail-based checks (blur, noise, screen-recapture) are measured at a
  normalised **working resolution** (longest side capped by
  `working_resolution`, default 1024). This keeps sharpness numbers comparable
  across a 2 MP webcam frame and a 12 MP phone photo; without it, large images
  look artificially blurry. The resolution check still reports true dimensions.
- **Thresholds are provisional.** The blur boundary was calibrated against a
  labelled set of roughly 60 real photographs (~90-95% agreement with human
  judgement on that set); the shadow and other cut-offs are calibrated more
  loosely. They behave sensibly on ordinary phone photos but have not been
  validated against a large, independent dataset. Expect to tune
  `CaptureTrustConfig` for your own images.
- **Two blur cases remain genuinely hard.** A blurry subject in front of a
  sharp background, and heavily textured motion blur (grass, foliage) whose
  streaks survive as high-frequency detail, can both be under-flagged, because
  a pixel-only sharpness measure cannot know which part of the frame was the
  intended subject. Handling these reliably needs subject/face detection, which
  is on the roadmap.
- The screen-recapture check is **off by default** from v0.1.3. In testing it
  raised a medium/high risk on the majority of ordinary photos (ornate objects,
  textures and printed patterns produce moiré-like energy), and it cannot be
  calibrated reliably without a labelled set of genuine screen recaptures. It
  remains available as an opt-in experiment and must never be treated as proof.
- Orientation is reported but the image is never rotated automatically, and
  only clear skew (>= 10 degrees) is surfaced - everyday handheld tilt is
  ignored.
- Document detection is a lightweight heuristic and may miss low-contrast or
  cluttered documents, or misidentify strong rectangular backgrounds.
- Noise and shadow detection are intentionally conservative to reduce false
  positives, which means subtle cases may go unflagged.
