# Security Policy

## Supported versions

CaptureTrust is at an early (0.x) stage. Security fixes are applied to the
latest released version. Please always run the most recent release.

## Reporting a vulnerability

If you discover a security issue, please **do not open a public GitHub issue**.
Instead, use GitHub's private
[security advisory](https://github.com/kriishgulati/capturetrust/security/advisories/new)
form, or email the maintainers at `kriish.gulati1703@gmail.com`.

Please include:

- A description of the issue and its impact.
- Steps to reproduce, or a proof-of-concept.
- Any suggested remediation.

We aim to acknowledge reports within a few business days.

## Privacy and data handling

CaptureTrust is designed to be safe by default:

- **Local processing only.** Images are analysed in your own Python process.
  The library makes no network calls and uploads nothing.
- **No telemetry.** The library does not collect or transmit any usage data.
- **No persistence.** The library does not write temporary files or logs of
  image content during normal operation.
- **Malformed input.** The library attempts to fail safely on corrupt or
  unsupported images by raising clear, typed exceptions rather than crashing.

## Important scope note

CaptureTrust estimates **visual quality**. It is **not** an anti-fraud,
tamper-detection, or identity-verification system, and its output must not be
used as the sole basis for legal, financial, employment, academic, insurance,
or identity decisions. Always include human review in high-impact contexts.
