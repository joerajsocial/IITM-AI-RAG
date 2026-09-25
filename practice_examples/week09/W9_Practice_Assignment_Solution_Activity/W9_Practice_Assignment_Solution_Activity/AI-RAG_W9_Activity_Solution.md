# AI-RAG · Week 9 · Activity Solution
## Failure analysis — instructor reference

> Reference answers and grading guidance for the W9 failure analysis
> activity. Use this in office hours and as model output that learners
> can self-compare against.
>
> The activity is a diagnostic-skill build, not a knowledge test. A
> learner with thoughtful root-cause attribution on 3 questions has
> done better than one with formulaic templated answers on 5. Grade
> for quality of reasoning, not completeness.

---

## Expected distribution of root causes

On our reference corpus (~24 chunks, 20 golden questions), W9
`hybrid_rerank` typically achieves precision@3 ≈ 0.75-0.85, which means
~3-5 questions fail. Across cohorts, the failures distribute roughly:

| Root cause | Frequency | Typical pattern |
|---|---|---|
| **Question ambiguity** | ~35% | Question has multiple valid interpretations; gold answer picks one but LLM picks another |
| **Generation failure** | ~25% | Right chunk retrieved; LLM mis-interpreted phrasing (double-negative, conditional, scope qualifier) |
| **Retrieval failure** | ~25% | Tokenisation gap, embedding-vs-query semantic gap, or chunk-boundary issue |
| **Reranker failure** | ~10% | Cross-encoder demoted the right chunk because it doesn't surface answer-keywords explicitly |
| **Corpus gap** | ~5% | Information genuinely not in corpus (rare for the reference set — we picked questions answerable from it) |

A learner reporting "all 5 failures are retrieval failures" is almost
certainly under-diagnosing. The point of the activity is precisely to
shift this default attribution.

---

## Walked example — three sample diagnoses

Here are three example failures that come up on most cohort runs, with
the model diagnostic for each. Use these as calibration when grading.

### Sample failure 1 — "How many days of paid leave does an employee get for the death of a parent?"

**Gold source:** `leave_policy.md`

**Top-3 retrieved:**
1. `parental_leave_handbook.md` / "Eligibility" / 0.412
2. `leave_policy.md` / "Bereavement Leave" / 0.387
3. `leave_policy.md` / "General Leave Provisions" / 0.241

**LLM answer:** *"According to the parental leave handbook, you may be
eligible for compassionate leave..."* [continues with information from
parental leave document]

**Was gold chunk in pre-rerank candidates?** Yes (rank 4 from BM25, rank 8
from dense)

**Was gold chunk in top-3?** Yes (rank 2)

**LLM answer quality:** Wrong — LLM cited the parental_leave document
(rank 1) instead of the bereavement leave section in leave_policy.md
(rank 2)

**Root cause: GENERATION FAILURE**

**Why:** The right chunk *was* retrieved and ranked second. The LLM picked
the first chunk to answer from because it appeared first in the context.
This is a generation prompt issue — the LLM is being too literal about
"use the documents provided" without enough guidance to pick the most
relevant among them.

**Proposed fix:** Update the system prompt to explicitly instruct the LLM
to evaluate which of the provided chunks is most relevant to the
question, rather than defaulting to the first. Alternative: increase k
from 3 to 5 so the LLM sees more context and can compare; this often
helps but adds tokens.

**Confidence:** High

---

### Sample failure 2 — "What is the carry-over allowance for unused annual leave?"

**Gold source:** `leave_policy.md`

**Top-3 retrieved:**
1. `leave_policy.md` / "Annual Leave Entitlement" / 0.654
2. `wfh_policy.md` / "Time off for remote workers" / 0.301
3. `expense_policy.pdf` / "Travel allowances" / 0.187

**LLM answer:** *"The leave policy mentions annual leave entitlement is
25 days per year. The carry-over allowance is not explicitly stated in
the retrieved documents."*

**Was gold chunk in pre-rerank candidates?** Yes (rank 1 in dense, rank 3 in BM25)

**Was gold chunk in top-3?** Yes (rank 1)

**LLM answer quality:** Correct — the LLM honestly said the answer wasn't
in the chunks

**Root cause: RETRIEVAL FAILURE** (sub-type: wrong-chunk-from-right-doc)

**Why:** The corpus DOES contain the carry-over information, but it's in
a different chunk of `leave_policy.md` ("Unused annual leave carries over
up to 5 days into the next leave year") than the one that was retrieved.
The "Annual Leave Entitlement" chunk has the 25-days fact, which is what
matched the question's keywords. The "Carry-over" content is in a later
section that didn't get scored highly.

**Proposed fix:** This is a chunk-boundary issue. The carry-over content
should ideally be in the same chunk as the entitlement (they're
semantically the same topic). Re-chunk this document with larger
target_size, OR merge the two sections at ingestion time, OR use
multi-query rewriting to generate variants like "how much annual leave
can I carry over" that would explicitly hit the carry-over chunk.

**Confidence:** High

---

### Sample failure 3 — "What's the rule for working from home?"

**Gold source:** `wfh_policy.md`

**Top-3 retrieved:**
1. `wfh_policy.md` / "Eligibility" / 0.521
2. `wfh_policy.md` / "Equipment" / 0.402
3. `vpn_setup.html` / "Remote access" / 0.298

**LLM answer:** *"To work from home, you must be eligible per the WFH
policy. Eligible roles include..."* [accurate summary of eligibility section]

**Was gold chunk in top-3?** Yes — chunks from gold_source were rank 1 AND 2

**LLM answer quality:** OK — answer is correct and grounded

**Root cause: QUESTION AMBIGUITY**

**Why:** This question is too vague. "The rule for working from home"
could mean: eligibility, equipment, days-per-week limits, manager
approval process, expense reimbursement, security requirements,
international policy, or any of several other aspects. The gold answer
in the golden set might be one specific aspect (perhaps "days-per-week
limit") but the LLM picked eligibility. Both are valid.

**Proposed fix:** This is *not* a retrieval problem. The gold question
should be more specific — "How many days per week can I work from
home?" — OR the system should detect underspecified questions and ask
for clarification. Adding more retrieval techniques won't help; the
retrieval is already working.

**Confidence:** Medium (would want to inspect the gold answer to confirm
the LLM's answer is *actually* a different valid interpretation, not a
worse interpretation of the same question)

---

## Sample summary section

A learner's final "Pattern summary" should look something like:

> Across my 5 failures:
> - 2 were generation failures (LLM didn't pick the right chunk among
>   retrieved candidates)
> - 1 was retrieval failure (chunk-boundary issue)
> - 1 was question ambiguity (vague question)
> - 1 was corpus gap (information not in the corpus)
>
> Most common: generation failure. The highest-leverage fix for my
> capstone is improving the system prompt to better discriminate among
> retrieved chunks. Adding more retrieval techniques (HyDE, multi-query)
> would help with the retrieval-failure case but wouldn't address the
> generation failures, which are 40% of my failure mode.

Reward this kind of summary — it shows the diagnostic muscle the
activity was designed to build.

---

## Grading rubric

| Criterion | Weight | What to look for |
|---|---|---|
| Followed template | 10% | All 5 sections have the prescribed structure |
| Inspected actual data | 25% | Specific chunks named, specific scores reported, not generic "I think retrieval failed" |
| Used decision flowchart | 20% | Diagnosis follows the Q1→Q4 evidence chain, not pattern-matched to a favourite cause |
| Diagnosis is plausible | 25% | The diagnosis matches the evidence provided in their inspection |
| Fix proposal is concrete | 15% | "Improve the prompt" is too vague; "add explicit chunk-selection guidance to the system prompt" is concrete |
| Pattern summary is honest | 5% | Doesn't artificially conclude "all retrieval failures need more retrieval techniques" |

A learner who attributes everything to retrieval failure gets full credit
on Template + Inspection but loses points on Diagnosis + Pattern. A
learner who attributes everything to question ambiguity (the trendy
diagnosis after this activity) similarly loses points if the evidence
doesn't support it.

---

## Common partial-credit patterns

### "I diagnosed it as retrieval failure, but I didn't check if the LLM had the right chunk"

Walk back to the decision flowchart. Did they check Q2 (was the gold
chunk in pre-rerank candidates)? If yes, they shouldn't have stopped at
"retrieval failure" — they need to check Q3 (rerank) and Q4 (generation).
The diagnostic discipline is to walk all four questions even when one
seems obvious.

### "All 5 of my failures were corpus gaps"

Unlikely on the reference corpus, which was designed to be answerable.
Possible signs: their golden set has questions that don't match their
actual corpus (e.g., they're using a different corpus than the W7-W8
reference). Worth a quick 1:1 to confirm they're running against
`capstone_chunks_v2` and not a stale collection.

### "The cross-encoder is broken"

Common over-attribution. Cross-encoders are deterministic and well-
trained; their reranks are usually defensible even when they don't match
the gold label. If a learner says "the reranker is broken," ask: "the
chunk it ranked higher — was it actually less relevant to the question
than the gold chunk, or just less keyword-overlapping?" If the chunk
isn't actually less relevant, the issue is gold-label quality, not the
reranker.

### "I'll fix it by adding HyDE/multi-query/step-back to every query"

Pattern-matches the W9 lab content but ignores the cost. Push back: "Of
your 5 failures, how many do you think HyDE would actually help? Why?"
Often the answer is "maybe 1 or 2 of the 5" — at which point applying
HyDE to every query is overcorrection.

---

## Tying back to the curriculum

The four-cause taxonomy in this activity is the foundation for W11's
LLM-judge eval framework. In W11, we formalise these into automated
detectors:

- **Retrieval failure detector** — does the answer mention any source
  document?
- **Generation failure detector** — does the answer contradict the
  retrieved chunks?
- **Question ambiguity detector** — would multiple interpretations
  produce different answers?
- **Corpus gap detector** — does the model express uncertainty in its
  answer?

A learner who built diagnostic intuition in this activity will find W11
intuitive. A learner who skipped or rushed this activity will struggle
with W11's evaluator design choices.

---

*End of activity solution. Pair with `AI-RAG_W9_Activity.md` for cohort
delivery.*
