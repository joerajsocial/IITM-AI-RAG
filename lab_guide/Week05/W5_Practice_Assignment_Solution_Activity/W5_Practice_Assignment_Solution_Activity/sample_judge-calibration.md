# Judge Calibration

**Date:** 17/03/2026
**Cohort member:** _Sample learner_
**Capstone:** Internal HR policy assistant for a mid-sized firm
**Sampled entries (10 of 20):** g001, g003, g005, g007, g009, g011, g015, g016, g019, g020 (6 happy, 3 harder, 1 edge)

## My scores (filled in blind — without looking at the judge)

| Golden id | My accuracy | My groundedness | My format | One-line note |
|---|---|---|---|---|
| g001 | 4 | 4 | 4 | Direct lookup, perfect citation |
| g003 | 3 | 3 | 4 | Right answer, weak source quotation |
| g005 | 4 | 4 | 3 | Correct but slightly verbose |
| g007 | 4 | 3 | 4 | Answer fine, sources implicit not explicit |
| g009 | 3 | 4 | 4 | Right answer, slightly oblique reasoning |
| g011 | 2 | 3 | 4 | Subtle confusion of "annual leave" vs "unpaid leave" |
| g015 | 4 | 4 | 3 | Comprehensive, format slightly off |
| g016 | 3 | 3 | 4 | Multi-hop, missed one of the conditions |
| g019 | 4 | 4 | 4 | Clean lookup |
| g020 | 2 | 2 | 3 | Hallucinated a policy clause that doesn't exist |

## Judge's verdicts (revealed after my blind scoring)

| Golden id | Judge accuracy | Judge groundedness | Judge format |
|---|---|---|---|
| g001 | 4 | 4 | 4 |
| g003 | 3 | 3 | 4 |
| g005 | 4 | 4 | 4 |
| g007 | 4 | 3 | 4 |
| g009 | 3 | 4 | 4 |
| g011 | 4 | 3 | 4 |
| g015 | 4 | 3 | 3 |
| g016 | 3 | 3 | 4 |
| g019 | 4 | 4 | 4 |
| g020 | 2 | 2 | 3 |

## Findings

### Agreement

- **Exact: 26 / 30 (87%)**
- **Within-1: 30 / 30 (100%)**

Per-dimension:
- Accuracy: 8 / 10 exact
- Groundedness: 9 / 10 exact
- Format: 9 / 10 exact

### Disagreements > 1 (the ones worth investigating)

- **g005 (format: 3 vs 4 — Δ=1, not >1)** — judge was more lenient
  on format. Within tolerance.
- **g009 (groundedness: 4 vs 4)** — agreement, no disagreement.
- **g011 (accuracy: 2 vs 4 — Δ=2)** — **real disagreement.** I
  scored 2 because the answer confuses "annual leave" with "unpaid
  leave" — a subtle but factually wrong substitution. The judge
  scored 4 because the answer was confident and well-formatted.
  **Verdict: the judge missed a real factual error.** Probably
  anchored on form over content.
- **g015 (groundedness: 4 vs 3 — Δ=1)** — within tolerance.

### Decision

Trust the judge for routine eval runs in W6+. Agreement is strong
(87% exact, 100% within-1) and the one Δ>1 disagreement is a
specific failure mode (judge missing factual errors when the
candidate is confidently formatted) that I can spot-check for
manually.

**Rubric sharpening to commit:** Tighten the level-4 anchor for
accuracy. Currently it says *"completely correct"*. Change to
*"completely correct, with no subtle substitutions, conflations, or
hedges that mislead"*. This makes the judge less forgiving of g011-
style confident-but-wrong answers.

I'll watch for this failure mode in W6 — if the judge over-scores
confidently-worded but factually-shaky answers, I'll consider
moving to gpt-4o as judge (currently using gpt-4o-mini, cheaper
but might be too generous).
