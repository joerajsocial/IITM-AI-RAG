# Rubric sharpening example

> A worked example showing how a calibration finding translates into
> a concrete rubric change. Use this in office hours to show learners
> what "sharpening based on calibration" looks like in practice.

## The finding

From the W5 calibration activity:

> **g011 (accuracy: 2 vs 4 — Δ=2)** — I scored 2 because the answer
> confused "annual leave" with "unpaid leave" — a subtle but
> factually wrong substitution. The judge scored 4 because the answer
> was confident and well-formatted.

## The rubric, before

```
Accuracy:
  4 — completely correct
  3 — mostly correct, minor inaccuracies
  2 — partially correct
  1 — incorrect
```

The problem with the level-4 anchor "completely correct": a judge
reading this can pattern-match on *confidence and form* and miss
*subtle factual errors*. The model knows what a confident, well-
formatted answer looks like — it might rate that a 4 even when
the substance is wrong.

## The rubric, after

```
Accuracy:
  4 — completely correct, with no subtle substitutions, conflations,
      or hedges that would mislead a careful reader
  3 — mostly correct; one minor inaccuracy that wouldn't mislead
  2 — partially correct; contains at least one substitution or
      conflation that would mislead
  1 — incorrect; main claim is false or unsupported
```

Two changes:

1. **Level 4 now names the failure mode** ("subtle substitutions,
   conflations, or hedges"). Judges follow instructions; if the
   rubric tells them what to look for, they'll look.
2. **Level 2 now describes the g011 case explicitly** ("substitution
   or conflation that would mislead"). The judge has a precedent
   for what a 2 looks like in this specific failure mode.

## How to validate the sharpening worked

Re-run the eval with the sharpened rubric. The g011 case should now
score 2 (or possibly 3), not 4. If it still scores 4, the change
didn't land — either the judge model is too weak or the rubric
needs more concrete examples.

## When NOT to sharpen

Don't sharpen for every disagreement. Reasons to leave the rubric
alone:

- **The disagreement is Δ=1.** Level boundaries are inherently
  fuzzy; some Δ=1 disagreement is normal.
- **You were wrong.** Genuinely. Sometimes the judge reads the
  candidate more carefully. Note these in your own calibration
  notes, don't change the rubric.
- **One-off failure mode.** If a disagreement type appears once
  in 30 dimension-scores, it's noise. If it appears 3+ times,
  it's a pattern worth fixing.
