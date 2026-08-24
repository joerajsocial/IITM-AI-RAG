# W5 Activity Solution — Judge calibration + golden set expansion

> *Instructor reference for the W5 take-home before DR#1. Two
> activities — Activity A (calibration, primary, 60 min) and
> Activity B (50-entry expansion, stretch, 60 min).*

**Activity time:** 60-90 min total
**Prerequisites:** W5 lab complete — `eval-run-001` exists, golden_set
has 20 entries, judge.py has a rubric
**Files involved:** `data/golden_set.jsonl`, `data/answers.db`, `src/eval/judge.py`, `docs/judge-calibration.md` (new)

---

## What this activity is testing

**Activity A — Calibration:** Can the learner *verify* their LLM
judge against themselves? This is the meta-skill that makes W6+
trustworthy: when retrieval changes, the learner can't sanity-check
20 entries manually every week, so they need to know if the judge
is calibrated.

**Activity B — Expansion (stretch):** Can the learner grow the golden
set with discipline (14/4/2 ratio preserved, real questions)? This
is the substrate quality lesson.

---

## Activity A — Reference walkthrough

### The mechanics

1. Pick 10 of 20 golden entries via **stratified sampling** (6 happy,
   3 harder, 1 edge — NOT random)
2. Score them yourself blind (no peeking at judge verdicts)
3. Reveal the judge's verdicts and compute agreement
4. Read disagreements, decide whether to trust the judge

### Expected agreement rates (the headline numbers)

| Agreement bucket | What it means | Action |
|---|---|---|
| Exact ≥ 70%, within-1 ≥ 95% | Strong rubric, trustworthy judge | Use judge in W6+ |
| Exact 50-70%, within-1 ≥ 90% | Rubric has ambiguity at level boundaries | Sharpen rubric once, then trust |
| Exact < 50%, within-1 < 90% | Rubric is vague OR judge model is too weak | Read disagreements; fix the cause |

### Where disagreements usually come from

Three common patterns the helper script will surface:

**Rubric ambiguity at level boundaries.** Learner scored a "4" for
groundedness, judge scored "3". Both read the same rubric.
Resolution: tighten the level-3 vs level-4 boundary in the rubric.

**Judge missing detail.** Learner scored "2" for accuracy because
they spotted a subtle factual error; judge scored "4". The judge's
reasoning paragraph reveals it didn't notice. If this happens more
than 2/10 times, the judge model is too weak.

**Learner generosity.** Learner scored "4" for groundedness because
the candidate "felt thorough"; judge scored "3" because there's no
explicit source citation. The judge is right; the learner is
calibrating upward.

### Sample disagreement to expect

```
g015: I scored a=4 / judge=2 (Δ=2)
  Reasoning:
    My note: "fully answers the question with good context"
    Judge note: "candidate confuses 'annual leave' with 'unpaid
                  leave' — factually inaccurate"

  Verdict: judge is right; I missed the leave-type confusion.
  No rubric change needed; my own calibration drifted high.
```

### What a strong calibration submission looks like

- 10 entries from a stratified sample (mix of buckets + score range)
- Blind scoring done (no peeking)
- Agreement metrics: exact + within-1
- Per-dimension breakdown (accuracy / groundedness / format)
- 2-3 disagreements explored with verdicts (rubric ambiguity / judge
  miss / learner miss)
- Decision: trust / sharpen / replace
- One concrete rubric tweak if applicable

### What a weak submission looks like

- Picked entries randomly instead of stratified
- Reflects the judge's scores (didn't go blind)
- Reports only one agreement metric
- No exploration of *why* disagreements happened
- Decision is "I trust the judge" without evidence

---

## Activity B — Expansion reference

### The plan-then-write order

The activity prescribes a 14/4/2 ratio. At 50 entries:

| Bucket | 20-entry mix | 50-entry mix | Need to add |
|---|---|---|---|
| Happy-path | 14 | 35 | +21 |
| Harder | 4 | 10 | +6 |
| Edges | 2 | 5 | +3 |

30 new entries = 21 happy + 6 harder + 3 edges. Learners should
**plan the categories first** (list under-covered topics) **then
write the entries**. The opposite order produces 30 happy-path
entries in 4 categories.

### Expected delta between eval-run-001 and eval-run-002

Most often: **averages move by < 0.2 between the two runs.** That's
expected — 30 new entries don't *systematically* change the average,
they give better resolution.

What *does* change: subgroup analysis becomes possible. At 50
entries split into ~10 categories, you can ask *"are leave
questions weaker than expense questions?"* — at 20 entries, every
category has 2-3 data points and you can't reliably answer.

### What to watch for in submissions

- New entries follow the same shape (`id`, `question`,
  `ideal_answer`, `notes`)
- IDs are sequential (g021-g050)
- The 14/4/2 ratio is preserved (or close)
- New entries cover *previously under-represented* categories, not
  just more of the same
- `validate_golden_set` runs cleanly (coverage is approximately
  `{happy: 35, harder: 10, edge: 5}`)
- Comparison note exists in `docs/eval-run-002.md`

---

## Office hours hot questions

- *"Can I peek at the judge's scores while I'm still scoring?"* —
  No. The calibration depends on independence. If you anchor on the
  judge, the activity is meaningless.
- *"Should I score all 20 instead of 10?"* — You can, but the time
  cost is 60 min instead of 30. The marginal information from the
  extra 10 entries is small unless your agreement rate is
  borderline.
- *"What if I disagree with the judge on every single entry?"* —
  Probably means either (a) your rubric and your mental model
  diverge — read it again carefully, or (b) the judge model is too
  weak. The disagreements will show you which.
- *"Do I have to do Activity B?"* — No. It's stretch. Only do it
  if Activity A finished in 45 min AND your DR#1 slot is >48 hours
  away.

---

## Common pitfalls

- **Peeking at judge scores.** Easy mistake. Hide them by working
  from the TSV the script generates (which excludes them).
- **Stratified sampling not done.** 10 random entries will under-
  represent harder/edge buckets, where the most interesting
  disagreements live.
- **Rubric change not committed.** If the calibration surfaces a
  rubric issue and the learner doesn't update `src/eval/judge.py`,
  the W6+ eval runs will continue using the broken rubric.
- **Eval-run-002 not committed.** Without the comparison row in
  `eval_runs`, future weeks can't reference the expansion.

---

## Files in this solution package

- `compute_calibration.py` — the helper script the activity mentions
  (reads judge-calibration.md + queries eval_runs table; prints
  agreement metrics)
- `sample_judge-calibration.md` — a complete sample submission
  showing both the blind scores and the post-reveal findings
- `judge_rubric_sharpening_example.md` — example of a good rubric
  tweak based on a calibration finding

---

*End of W5 solution.*
