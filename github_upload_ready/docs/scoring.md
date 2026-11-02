# Scoring

CaptureTrust turns a set of heuristic checks into a single, explainable score.

## How the score is calculated

1. The score starts at **100**.
2. For every enabled check that did **not** pass, a deduction is subtracted
   based on the check and its severity (`low`, `medium`, `high`).
3. The final score is clamped to the range **0–100**.
4. Every deduction is recorded — check, severity, amount, and a human-readable
   reason — under `metrics.score_explanation` in the report.

The score is **deterministic**: the same image and configuration always produce
the same result.

## Default deduction table

| Check | low | medium | high |
| --- | --- | --- | --- |
| blur | 8 | 24 | 40 |
| resolution | 12 | 16 | 20 |
| lighting | 7 | 14 | 22 |
| glare | 8 | 15 | 22 |
| noise | 5 | 10 | 15 |
| shadow | 5 | 10 | 16 |
| document_framing | 8 | 16 | 25 |
| screen_recapture | — | 10 | 20 |

`screen_recapture` has no `low` deduction: a low risk contributes nothing.

## What a deduction means

A deduction is a transparent statement that a specific check found a specific
severity of problem, along with the reason. It is **not** a probability, a
confidence, or a fraud weighting — it is an auditable quality penalty.

## Confidence label

Alongside the score, the report includes a `confidence` label (`low`, `medium`,
`high`). Confidence reflects how many usable signals were available and how
clear they were, not how "good" the image is. An image can score high with only
medium confidence if few signals could be computed.

## Customising thresholds and deductions

Two independent levers exist:

- **Thresholds** on `CaptureTrustConfig` (for example `blur_threshold`,
  `glare_threshold`, `min_width`) change *when* a check reports a problem.
- **Deduction overrides** change *how much* a reported problem costs:

  ```python
  from capturetrust import CaptureTrustConfig, inspect_image

  config = CaptureTrustConfig(
      deduction_overrides={"blur": {"high": 40}, "noise": {"low": 2}},
  )
  report = inspect_image("photo.jpg", config=config)
  ```

Disabled checks never contribute to the score. Document framing is never
penalised when no document is detected, so the library is equally usable for
non-document photos.

## Why the score is not a legal or fraud conclusion

The score summarises heuristic *visual quality* signals only. It cannot and does
not determine authenticity, identity, or intent. It must not be used as the sole
basis for legal, financial, employment, academic, insurance, or identity
decisions. In high-impact contexts, treat the score as a triage aid and keep a
human in the loop. See [limitations.md](limitations.md).
