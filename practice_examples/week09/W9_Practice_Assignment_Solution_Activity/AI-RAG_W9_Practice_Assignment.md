# AI-RAG · Week 9 · Activity
## Failure analysis — Why does retrieval still fail?

> **Take-home · 60 min · solo or pairs**
>
> By the end of W9, you have the strongest retrieval stack of the curriculum
> so far: hybrid (BM25 + dense via RRF) + cross-encoder reranking. And yet —
> some questions still fail. This activity is about figuring out *why*.

---

## Why this activity matters

A common new-engineer instinct when retrieval fails: "Add another technique."
Hybrid not enough? Add rerank. Rerank not enough? Add HyDE. HyDE not enough?
Add multi-query.

That instinct is wrong. Each new technique adds latency, cost, and code
complexity — and the lift from stacking techniques diminishes fast. The
disciplined alternative is: **diagnose why each failure happened, then fix
the specific root cause**.

Four root causes account for ~95% of retrieval failures in practice:

| Root cause | What it looks like | Fix category |
|---|---|---|
| **Retrieval failure** | Right answer chunk exists in corpus, but no method retrieved it in top-K | Tokenisation, chunk boundaries, embedding model, query rewriting |
| **Generation failure** | Right chunk *was* retrieved, but LLM produced wrong/incomplete answer | Prompt engineering, model choice, generation parameters |
| **Question ambiguity** | The question itself has multiple valid interpretations | Question reformulation, clarification UX |
| **Corpus gap** | The information isn't in the corpus at all | Corpus expansion, "I don't know" handling |

If you can't tell which category a failure falls into, you'll waste time
adding the wrong technique. This activity builds the diagnostic muscle that
prevents that.

---

## What you'll do

Pick **5 questions** where W9's best method (`hybrid_rerank`) still failed —
i.e., precision@3 was 0.0 on those questions in your `wk9-precision-delta.md`.

For each failed question, you'll:

1. **Read the question** carefully
2. **Inspect what was retrieved** in the top-3
3. **Inspect what the LLM generated** as the answer
4. **Inspect what the corpus actually contains** about the topic
5. **Diagnose the root cause** (one of the four categories above)
6. **Propose a fix** that addresses that specific root cause

Deliverable: `docs/wk9-failure-analysis.md` with one section per question.

---

## Step 1 — Identify your 5 failed questions (5 min)

Open `docs/wk9-precision-delta.md` (from Step 2 of the lab). Find the 5
questions where `precision@3 (hybrid_rerank)` is **0.0** — i.e., none of the
top-3 chunks came from the `gold_source`.

If you have fewer than 5 such questions (lucky you), use the ones with the
lowest precision@3 next. If you have more than 5, pick a mix: a couple that
seem like they should be easy, and a couple that look genuinely hard.

Record the question IDs in a scratch file. You'll work through them one
at a time.

---

## Step 2 — Inspect the retrieved chunks (10 min per question)

For each failed question, run an isolated retrieval to see what you got:

```python
from src.rag.qdrant_store import load_store
from src.rag.qdrant_rag import ask_rag
from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant

store = load_store(embedding_model="text-embedding-3-small", dim=1536)
chunks = load_chunks_from_qdrant(store)
bm25 = build_bm25_index(chunks)

q = "your failed question here"

# Run hybrid_rerank with k=5 instead of k=3 — see the next 2 as well
result = ask_rag(q, store, k=5,
                 retrieval_method='hybrid_rerank',
                 bm25_index=bm25, chunks=chunks)

print(f"\n=== Question: {q} ===")
print(f"\nLLM answer:\n{result['answer']}\n")
print(f"Retrieved sources (top-5):")
for i, cit in enumerate(result['citations'], 1):
    print(f"  {i}. {cit['source']} | section: {cit['section_path']}")
    print(f"     score: {cit['score']:.3f}")
    print(f"     dense_rank: {cit['dense_rank']}, bm25_rank: {cit['bm25_rank']}, pre_rerank_rank: {cit['pre_rerank_rank']}")

print(f"\nLatency: {result['latency_ms']}ms (embed={result['embed_ms']}, retrieve={result['retrieve_ms']}, generate={result['generate_ms']})")
```

Note:
- What documents/sections appeared in top-5
- Are any from the right document (gold_source)?
- If yes — they were ranked too low; what beat them?
- If no — was the right document in the corpus at all?

---

## Step 3 — Inspect the corpus directly (10 min per question)

You need to know what the corpus actually contains about the topic. Search
your golden source document directly:

```python
# Find all chunks from the gold source document
gold_chunks = [c for c in chunks if c['source'] == 'YOUR_GOLD_SOURCE.md']
print(f"\nGold source has {len(gold_chunks)} chunks. Sample texts:")
for c in gold_chunks[:5]:
    print(f"\n  --- {c['section_path']} ---")
    print(f"  {c['text'][:200]}...")
```

Or grep the original document:

```bash
grep -in "vacation\|leave\|annual" data/corpus/leave_policy.md
```

You're answering:
- Is the answer actually in the corpus?
- If yes, which chunk(s) contain it?
- Were those chunks scored by your retrieval methods, even if low?

---

## Step 4 — Diagnose the root cause (10 min per question)

Use this decision flowchart. Walk through it for each failed question:

```
START
  │
  ▼
Q1: Is the answer actually in the corpus at all?
  │
  ├─ NO ──────────────────► CORPUS GAP
  │                          (Even perfect retrieval can't help.)
  │
  └─ YES
      │
      ▼
Q2: Was the answer-bearing chunk in the top-20 candidates (pre-rerank)?
      │
      ├─ NO ──────────────► RETRIEVAL FAILURE
      │                      (Hybrid retrieval missed it entirely.)
      │                      → Suspect: tokenisation, chunk boundaries,
      │                        embedding-vs-query semantic gap, BM25 IDF
      │                        quirk, missing payload filter.
      │
      └─ YES (it was a candidate but didn't make top-3)
          │
          ▼
Q3: Did the cross-encoder rerank it to top-3?
          │
          ├─ NO ──────────► RERANKER FAILURE (sub-type of retrieval failure)
          │                  (Reranker scored wrong chunks higher.)
          │                  → Suspect: chunk text doesn't mention the
          │                    answer-relevant keywords; chunk is the
          │                    right document but wrong section.
          │
          └─ YES (top-3 contained the right chunk)
              │
              ▼
Q4: Did the LLM produce a wrong/incomplete answer despite having the right chunk?
              │
              ├─ YES ──────► GENERATION FAILURE
              │                (The retrieval worked; the LLM didn't.)
              │                → Suspect: prompt is unclear; LLM tripped
              │                  over a phrasing in the chunk (e.g.,
              │                  double-negative); chunk text needed more
              │                  context to be unambiguous.
              │
              └─ NO ────────► QUESTION AMBIGUITY
                              (LLM answered a different valid interpretation
                              than the golden answer.)
                              → Suspect: question itself is ambiguous; the
                              gold answer is one valid interpretation but
                              not the only one.
```

The questions in the flowchart map cleanly to the data you collected in
Steps 2-3. If you can't answer one, you don't have enough data yet —
go back and collect more.

---

## Step 5 — Propose a fix (5 min per question)

For each root cause, the **categorical** fix is different. You're not
required to *implement* the fix in this activity — just propose it
concretely.

### If RETRIEVAL FAILURE

- Specific term not in chunk text but in question? → **tokenisation review**:
  is the BM25 tokeniser splitting differently from your query? Is the
  chunker dropping section headings?
- Synonym mismatch (question uses "vacation," chunk uses "leave")?
  → **HyDE** is a candidate fix — generates hypothetical that uses
  corpus-like vocabulary
- Chunk too big and the answer-bearing sentence got buried?
  → **chunk size review** — drop target_chunk_size from 500 to 300
- Chunk too small and the answer needs more surrounding context?
  → **chunk size review** in the opposite direction
- Filter missing? → **payload filter** — does the question imply
  `doc_type='hr'` or similar?

### If RERANKER FAILURE

- The "right" chunk got reranked low because it doesn't mention the
  question's keywords explicitly? → consider whether your golden answer is
  on the right chunk — sometimes the gold label is wrong and the chunk
  *truly* doesn't contain the answer

### If GENERATION FAILURE

- Wrong/incomplete LLM answer despite right chunk?
  → **prompt engineering**: add explicit instruction to use only the
  provided context; add explicit instruction to say "I don't know" if
  uncertain
- Tripping over a phrasing pattern (double-negative, conditional, etc.)?
  → upgrade to gpt-4o or gpt-4o-2024-08-06 for that question pattern

### If QUESTION AMBIGUITY

- Multiple valid interpretations?
  → **question reformulation**: the gold question itself needs to be
  more specific, OR the system needs a clarification step ("Did you mean
  X or Y?")
- This is **not** a retrieval problem; no amount of new techniques fixes it

### If CORPUS GAP

- Information genuinely not in the corpus?
  → **corpus expansion**: add the source document
- Or: **explicit "I don't know" handling** if expansion isn't feasible

---

## The deliverable: `docs/wk9-failure-analysis.md`

Use this template (copy it and fill in 5 sections):

```markdown
# W9 Failure Analysis

5 questions where hybrid_rerank still failed. Root cause categories:
retrieval / reranker / generation / question / corpus.

---

## Question N (id: golden_set_question_<id>)

**Question:** [paste the question]

**Gold source:** [filename]

**Top-3 retrieved:**
1. [source / section / score]
2. [source / section / score]
3. [source / section / score]

**LLM answer:** [paste]

**Was the gold chunk in candidates (pre-rerank top-20)?** Yes / No

**Was the gold chunk in top-3 after rerank?** Yes / No

**LLM answer quality given retrieved chunks:** OK / Wrong / Incomplete

**Root cause:** [one of: retrieval / reranker / generation / question / corpus]

**Why:** [1-2 sentence diagnosis]

**Proposed fix:** [concrete proposal addressing the root cause]

**Confidence in diagnosis:** High / Medium / Low

---

## Question 2

...

(repeat for all 5)

---

## Pattern summary

Across the 5 failures, the most common root cause was: [category]

This suggests the highest-leverage fix for the capstone is: [fix category]
```

---

## Submission criteria

Commit `docs/wk9-failure-analysis.md` with:

- [ ] 5 questions analysed (or as many failures as you have, if fewer)
- [ ] Each section follows the template
- [ ] Root cause picked from the four categories
- [ ] Concrete fix proposal that addresses the specific root cause
- [ ] Pattern summary at the end naming the most common root cause

```bash
git add docs/wk9-failure-analysis.md
git commit -m "W9 activity: failure analysis on 5 hybrid_rerank failures"
```

---

## Tips from instructor experience

**Don't trust the precision@3 number alone.** A question that scores 0.0
on precision@3 might still have got the right answer if the LLM was good
at extracting from the wrong chunks. Read the actual LLM answer.

**Don't trust the LLM answer alone.** The LLM might produce a plausible-
looking wrong answer with high confidence. Cross-check against the gold
source document.

**Most failures are corpus or question issues, not retrieval.** First-time
analysts overestimate retrieval failure as the cause. It's often (~30%)
the actual cause; the other 70% is question ambiguity, corpus gap, or
generation. The point of this activity is calibrating that intuition.

**The "right" fix is usually surprising.** Stacking HyDE + multi-query +
step-back is rarely the right answer. Improving one chunk's text, or
clarifying one question, or adding one source document, usually has more
leverage than another retrieval technique.

**This sets up W11.** When we introduce the LLM-judge eval framework in
W11, we'll formalise these four root causes into automated detectors.
The diagnostic intuition you build here is what makes the W11 evaluators
make sense.

---

*60 minutes total. If you finish faster, do a sixth question. If you go
over, stop at 60 and submit what you have — partial credit beats no
submission.*
