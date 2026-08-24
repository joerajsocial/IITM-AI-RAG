# Week 5 — Take-home Activity

**Prompting + Eval Literacy + M1 [DR #1]**
Phase 1 · Foundations · CLOSING WEEK
**Self-paced · ~60-90 minutes · between Day 2 and your DR #1 slot**

---

## What this is

The W5 lab gets you to an **M1 evaluation baseline** — `eval-run-001.md`
with 20 entries judged by `gpt-4o`. The take-home activity extends that
work in two ways:

- **Primary (60 min):** Calibrate your LLM judge against yourself. You
  manually score 10 of your 20 golden entries without looking at the
  judge's verdicts. Then you compare. The disagreements tell you whether
  to trust the judge in W6+ — when retrieval changes the answer
  distribution and you can't sanity-check 20 entries manually every week.
- **Stretch (60 min):** Grow your golden set from 20 to 50 entries.
  Better signal at the cost of more upfront work. Optional; do this if
  you're aiming for a high DR #2 trajectory in W12.

Both are **before** your DR #1 slot, not after. The findings from Activity
A often surface a rubric issue you'd want to fix before defending the
baseline.

---

## Why it matters

**Activity A — calibration.** Every LLM judge has biases. The W5 deck
named three (length, position, self) and gave one mitigation each. But
the most important mitigation is the one you do yourself: spot-check.
This activity formalises the spot-check into a measurement — agreement
rate. If you and your judge agree on 25 of 30 dimension-scores (83%),
you can probably trust the judge for routine eval runs. If you agree on
15 of 30 (50%), something's wrong — usually the rubric is too vague,
sometimes you and the judge are evaluating against different mental
models of "good".

**Activity B — expansion.** 20 entries is the floor. 50 is where you can
*start* to detect category-level patterns ("the multi-hop questions are
systematically worse"). At 100+ you can do real subgroup analysis. The
W5 lesson plan calls 50 "early signal you can trust"; W11's formal eval
frameworks (RAGAS, DeepEval) assume at least that many.

---

## Prerequisites

Before starting, you should have these committed from the W5 lab:

- [ ] `data/golden_set.jsonl` — 20 entries with 14/4/2 coverage
- [ ] `src/eval/judge.py` — your filled-in rubric prompt
- [ ] `data/answers.db` with the `eval_runs` table populated by `eval-run-001`
- [ ] `docs/eval-run-001.md` — your baseline summary

If any of these are missing, **do the lab first**. The activity won't
work without the baseline.

---

# Activity A — Judge Calibration (Primary, ~60 min)

## Goal

By the end of this activity you have:

- `docs/judge-calibration.md` — a one-page summary with your agreement rate
- A clear answer to *"do I trust my LLM judge for routine eval runs?"*
- 1–2 sharpenings to your rubric prompt, if the disagreements surface them

## Step 1 — Pull 10 candidate answers from the eval baseline (5 min)

You'll score 10 of the 20 entries yourself. Pick the 10 by **stratified
sampling** — not random. You want:

- 6 from happy-path (the largest bucket)
- 3 from harder
- 1 from edges

Optionally mix in entries the judge scored 4/4 with entries it scored ≤2,
so you cover the score range.

Pull the candidate answers + ideal answers from your database:

```bash
sqlite3 -header -separator $'\t' data/answers.db <<'SQL' > /tmp/candidates.tsv
SELECT
    golden_id,
    question,
    candidate_answer,
    ideal_answer
FROM eval_runs
WHERE eval_run_label = 'eval-run-001'
  AND golden_id IN ('g001','g003','g005','g007','g009','g011','g015','g016','g019','g020')
ORDER BY golden_id;
SQL

wc -l /tmp/candidates.tsv
```

Change the 10 ids to your own stratified sample. The TSV gives you what
you'll score, *without* showing the judge's verdicts.

## Step 2 — Score the 10 yourself, blind to the judge (~30 min)

Create a scoring sheet. Three columns per entry: `accuracy`,
`groundedness`, `format` — each 1–4, matching the rubric levels.

**Crucially: don't look at the judge's `accuracy` / `groundedness` /
`format` columns yet.** That's the calibration. If you peek, you anchor
on the judge's scores and the activity collapses.

```bash
cat > docs/judge-calibration.md << 'EOF'
# Judge Calibration

**Date:** _<dd/mm/yyyy>_
**Cohort member:** _<your name>_
**Capstone:** _<one-line>_
**Sampled entries (10 of 20):** _<list ids, e.g. g001, g003, g005, ...>_

## My scores (filled in blind — without looking at the judge)

| Golden id | My accuracy | My groundedness | My format | One-line note |
|---|---|---|---|---|
| g001 | _<1-4>_ | _<1-4>_ | _<1-4>_ | _<one line — what tipped your score>_ |
| g003 | _ | _ | _ | _ |
| g005 | _ | _ | _ | _ |
| g007 | _ | _ | _ | _ |
| g009 | _ | _ | _ | _ |
| g011 | _ | _ | _ | _ |
| g015 | _ | _ | _ | _ |
| g016 | _ | _ | _ | _ |
| g019 | _ | _ | _ | _ |
| g020 | _ | _ | _ | _ |
EOF
$EDITOR docs/judge-calibration.md
```

While scoring, **use the same rubric your judge uses** — your own
`RUBRIC_PROMPT` from `src/eval/judge.py`. The point is to evaluate
against the same definitions; otherwise you and the judge are measuring
different things.

Take ~3 minutes per entry. Read the question, read the ideal, read the
candidate, score it. Resist the temptation to be more lenient or harsher
than the rubric calls for.

## Step 3 — Pull the judge's verdicts and compute agreement (~10 min)

Now reveal the judge's scores:

```bash
sqlite3 -header -column data/answers.db <<'SQL'
SELECT
    golden_id, accuracy AS a, groundedness AS g, format AS f
FROM eval_runs
WHERE eval_run_label = 'eval-run-001'
  AND golden_id IN ('g001','g003','g005','g007','g009','g011','g015','g016','g019','g020')
ORDER BY golden_id;
SQL
```

Paste this output into your `docs/judge-calibration.md` under a new
section, alongside your scores. Then compute agreement.

There are two natural agreement metrics:

- **Exact agreement:** for each of the 30 dimension-scores (10 entries
  × 3 dimensions), how many match exactly?
- **Within-1 agreement:** how many are within ±1 of each other?

Use the script (see Step 4) or compute by hand from a side-by-side
table:

```
| id   | my a / judge a | my g / judge g | my f / judge f | match (a, g, f) |
|------|----------------|----------------|----------------|-----------------|
| g001 |   3   /  3     |   4   /  3     |   3   /  4     |  ✓   ✗±1  ✗±1   |
| g003 | ...            |                |                |                  |
```

Then:

- **Exact agreement rate:** _<X>_ / 30 = _<XX>%_
- **Within-1 agreement rate:** _<X>_ / 30 = _<XX>%_

## Step 4 — (Optional helper) compute_calibration.py

If you'd rather have the agreement computed automatically, the helper
script `AI-RAG_W5_compute_calibration.py` reads your judge-calibration.md
markdown table (the "My scores" section) plus the eval_runs table and
prints the agreement metrics.

```bash
cp <bundle>/AI-RAG_W5_compute_calibration.py scripts/compute_calibration.py

python scripts/compute_calibration.py \
    --calibration-file docs/judge-calibration.md \
    --db               data/answers.db \
    --label            eval-run-001
```

You'd see:

```
Calibration summary
-------------------
  n entries           : 10
  n dimension-scores  : 30
  exact agreement     : 22 / 30  (73%)
  within-1 agreement  : 29 / 30  (97%)
  per-dimension exact :
    accuracy          : 7 / 10
    groundedness      : 6 / 10
    format            : 9 / 10
  disagreements > 1   : 1
    g015: I scored a=4 / judge=2 (Δ=2). I rated higher on accuracy.
```

## Step 5 — Read the disagreements and decide (~15 min)

The agreement number is the *headline*; the disagreements are the
*finding*. For every disagreement of 1 or more, look at the entry
(question + candidate + ideal) and ask three questions:

1. **Is the disagreement because my rubric is ambiguous?** Both of us
   read the rubric and reached different conclusions — typically this
   means a level boundary is poorly defined (e.g. what separates a "3"
   from a "4" on groundedness). Sharpen the rubric.
2. **Is the disagreement because the judge missed something?** The
   judge's reasoning paragraph tells you. Sometimes the judge anchors
   high (a known weak-judge symptom) and misses a real problem in the
   candidate. If this is more than 2 of 10, your judge model isn't
   strong enough.
3. **Is the disagreement because I was wrong?** Genuinely. Sometimes the
   judge reads the candidate more carefully than you do. Note these — they
   teach you about your own evaluation biases.

Write a short "Findings" section in `docs/judge-calibration.md`:

```markdown
## Findings

### Agreement
- Exact: _<X>_ / 30 (_<XX>_%)
- Within-1: _<X>_ / 30 (_<XX>_%)

### Disagreements > 1 (the ones worth investigating)
- **g015 (a: 4 vs 2):** I rated higher because <reason>. Looking at the
  judge's reasoning, the issue is <ambiguity in rubric / judge missed
  detail / I was generous>.
- _<your other Δ>1 cases>_

### Decision
- _One sentence: do you trust the judge for routine eval runs?_
- _One change to your rubric (if any): "I'll tighten the Level-3 anchor
  for groundedness — Level 3 should require citation; Level 4 should
  require explicit source quote."_
```

## Step 6 — Commit (~5 min)

```bash
git add docs/judge-calibration.md
# Plus any rubric changes you made:
git add src/eval/judge.py
git commit -m "Judge calibration — agreement <XX>% / within-1 <YY>%"
```

## What "good" looks like

- **Exact agreement ≥ 70%, within-1 ≥ 95%.** Strong rubric, trustworthy
  judge for routine eval runs.
- **Exact 50-70%, within-1 ≥ 90%.** Rubric has ambiguity at the level
  boundaries. Worth one round of sharpening before relying on the judge
  in W6+.
- **Exact < 50%, within-1 < 90%.** Either your rubric is genuinely vague
  or your judge model is too weak. Read the disagreements; the pattern
  tells you which.

---

# Activity B — Expand to 50 Entries (Stretch, ~60 min)

## Goal

A 50-entry golden set with the same coverage discipline, and a second
eval baseline run that compares to `eval-run-001`.

## When to do this

- You finished Activity A in 45 minutes.
- You're aiming for a high DR #2 (W12) trajectory.
- Your DR #1 slot is more than 48 hours away.

If any of those isn't true, skip Activity B — your time is better spent
on rubric sharpening from Activity A.

## Step 1 — Audit the 20 (~10 min)

Open `data/golden_set.jsonl` and look at the **categories** of your
happy-path entries. Common pattern: 4 leave-related, 4 expense-related,
2 working-week, 2 BYOD, 2 dress code. You've covered some categories
heavily and missed others.

List the categories you've covered well, the categories you've
under-covered, and the categories you've missed entirely. The 30 new
entries should fill the gaps.

## Step 2 — Plan the 30 new entries (~5 min)

Preserve the 14/4/2 ratio at scale:

| Bucket | 20-entry mix | 50-entry mix | Need to add |
|---|---|---|---|
| Happy-path | 14 | 35 | +21 |
| Harder | 4 | 10 | +6 |
| Edges | 2 | 5 | +3 |

So 30 new entries = 21 happy + 6 harder + 3 edges.

Sketch them on paper or in a scratch file (a table mapping new id to
category + brief question seed) before writing.

## Step 3 — Write the 30 entries (~30 min)

Numbered `g021` to `g050`. Same shape as the originals (`id`,
`question`, `ideal_answer`, `notes`). Same sourcing discipline (real
users > domain-expert imagined > you).

Add the entries to `data/golden_set.jsonl`:

```bash
# Just append to the file
cat >> data/golden_set.jsonl << 'EOF'
{"id": "g021", "question": "...", "ideal_answer": "...", "notes": "happy-path. ..."}
{"id": "g022", "question": "...", "ideal_answer": "...", "notes": "happy-path. ..."}
...
EOF
```

Validate:

```bash
python -c "from src.eval.golden import validate_golden_set; r = validate_golden_set('data/golden_set.jsonl'); print(r['coverage'])"
```

Expected: `{'happy': 35, 'harder': 10, 'edge': 5}` (or close).

## Step 4 — Re-run the eval with label `eval-run-002` (~15 min)

```bash
python scripts/run_eval.py \
    --golden-set data/golden_set.jsonl \
    --db         data/answers.db \
    --api-url    http://localhost:8000 \
    --judge-model gpt-4o \
    --label      eval-run-002
```

This costs ~$0.50–1.00 (50 entries × 1 judge call). Worth it.

## Step 5 — Compare eval-run-001 (20 entries) to eval-run-002 (50 entries) (~10 min)

```bash
sqlite3 -header -column data/answers.db <<'SQL'
SELECT
    eval_run_label,
    COUNT(*) AS n,
    ROUND(AVG(accuracy), 2) AS avg_accuracy,
    ROUND(AVG(groundedness), 2) AS avg_groundedness,
    ROUND(AVG(format), 2) AS avg_format
FROM eval_runs
WHERE eval_run_label IN ('eval-run-001', 'eval-run-002')
GROUP BY eval_run_label
ORDER BY eval_run_label;
SQL
```

Most often: averages move by less than 0.2 between the two runs. That's
expected — the 30 new entries don't *systematically* change the average,
they just give you better *resolution*.

What changes is your ability to spot category patterns. With 50 entries
split into ~10 categories, you can ask "are the leave questions weaker
than the expense questions?" — at 20 entries, every category has 2-3
data points and you can't really answer.

Add a one-paragraph note to `docs/eval-run-001.md` (or create
`docs/eval-run-002.md`) capturing the comparison.

## Step 6 — Commit

```bash
git add data/golden_set.jsonl docs/eval-run-*.md
git commit -m "Stretch — golden set extended to 50 (eval-run-002, avg <X.XX>)"
```

---

## Reflection prompts (for both activities)

After committing, sit with these for 5 minutes. You'll get more out of
DR #1 if you've actually thought about them, not just executed the steps.

1. **Trust.** Do you trust your LLM judge for the next 4 weeks of W6
   retrieval work — when you can't manually score 20 entries every
   week? If yes, what does the calibration agreement say to back that
   up? If no, what changes — a better judge model, a sharper rubric,
   a second judge for cross-checking?

2. **Discipline.** What's the smallest sustainable eval cadence for the
   next 4 weeks? Some learners run eval after every prompt change
   (high signal, high cost); some run weekly (lower signal, lower
   friction). Pick a cadence that matches your iteration speed.

3. **The thing you can't see.** What category of question is *missing*
   from your golden set today? You can't measure what you don't have
   entries for. List 2-3 categories you'd add if you grew to 100 — and
   make a note to revisit them by M2 (W12).

---

## Deliverables checklist

By the time you're at DR #1, this should be in your repo:

- [ ] **(Primary)** `docs/judge-calibration.md` with agreement metrics + findings
- [ ] **(Primary)** Any sharpening commits to `src/eval/judge.py` (the `RUBRIC_PROMPT`)
- [ ] **(Stretch, optional)** `data/golden_set.jsonl` extended to 50 entries
- [ ] **(Stretch, optional)** `eval-run-002` rows in the `eval_runs` table + comparison note
- [ ] At least one of the reflection answers (a sentence each) in your DR #1 1-pager's *"Open questions you're sitting with"* section
