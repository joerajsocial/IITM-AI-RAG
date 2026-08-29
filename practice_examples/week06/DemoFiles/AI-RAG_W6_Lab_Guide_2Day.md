# AI-RAG · Week 6 · Lab Guide
## Naive RAG from Scratch — Concept Demo

> **Two 90-minute in-session notebooks · standalone Jupyter · Track A**
>
> **Day 1:** Build the pipeline from scratch. Every stage as a separate cell.
> **Day 2:** Take the pipeline you built, vary every knob, and diagnose failures.
>
> These have nothing to do with the capstone — that's on purpose. Track A
> teaches the concept in isolation.
>
> **After the two sessions:** work through `AI-RAG_W6_Application_Growth_Guide.md`
> to add the same pattern to your capstone (self-paced take-home).

---

## Package contents

Inside `demos/`:

| File | Session | Purpose |
|---|---|---|
| `wk06_day1_naive_rag_build.ipynb` | Day 1 (90 min) | Build the pipeline stage-by-stage |
| `wk06_day2_pipeline_deep_dive.ipynb` | Day 2 (90 min) | Vary every knob, construct failures |
| `wk06_pipeline.py` | Helper | Day 1's code, importable by Day 2 (no rebuild) |

---

## Prerequisites (both days)

- [ ] Vocareum notebook environment (or local Jupyter with Python 3.10+)
- [ ] `openai`, `numpy` installed
- [ ] `OPENAI_API_KEY` set (`export OPENAI_API_KEY=sk-...`)
- [ ] Notebook file open

If any are missing, Cell 1 of the notebook will fail loudly — by design.

**Total cost across both notebooks: ~$0.02** in OpenAI credits.

---

## Day 1 · `wk06_day1_naive_rag_build.ipynb` (90 min)

Aligned to deck Topics 1, 2, 3: *Why RAG matters · RAG anatomy · Build naive RAG*.

### What we build
A complete naive RAG pipeline in ~100 lines of Python. Every stage of the arrow
chain (`docs → chunks → embeddings → cosine → top-K → prompt → answer`) is a
separate notebook cell.

**Corpus:** 10 short paragraphs about hot beverages. Deliberately non-enterprise
— this is concept isolation, not a capstone extension.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup (imports, OpenAI key check) | 2 min |
| 2 | The corpus — 10 hardcoded paragraphs | 3 min |
| 3 | Chunking (sliding window function) | 5 min |
| **3.5** | **Chunking strategies compared** — sliding vs sentence vs paragraph | **10 min** |
| 4 | Embedding — batch call to OpenAI | 8 min |
| 5 | Cosine similarity — rank all chunks for one query | 10 min |
| **5.5** | **Similarity playground** — try 5 different queries and observe | **10 min** |
| 6 | Top-K retrieval function | 5 min |
| 7 | Prompt construction — print exact prompt sent to LLM | 10 min |
| 8 | Generate — chat completion → answer + sources | 5 min |
| **8.5** | **Change the system prompt** — strict vs permissive vs no-instruction | **10 min** |
| 9 | Break it — 4 failure modes to discuss | 12 min |

**Bold rows are the extensions** that turn a 60-min pipeline build into a
90-min deeper exploration.

### Discussion moments (built into the notebook)

- **Cell 3.5:** which chunking strategy would you use? Sliding wins on simplicity;
  sentence-based wins on cleanliness; paragraph loses when docs are too long.
- **Cell 5.5:** try more queries. Which produce a clear winner? Which return
  many equally-close chunks?
- **Cell 8.5:** how much does the system prompt change the answer? Which
  variant would you ship?
- **Cell 9 (all four failure modes):** what does each failure mode teach us
  about where naive RAG will break in production?

### What learners take away from Day 1

By end of Cell 9 they should:
1. Draw the full pipeline from memory
2. Explain what an embedding is (numbers, non-interpretable, similar meanings → similar vectors)
3. Understand cosine similarity as a distance metric
4. Recognise that the LLM only sees what you put in the prompt
5. Name 3+ ways naive RAG will fail

---

## Day 2 · `wk06_day2_pipeline_deep_dive.ipynb` (90 min)

Aligned to deck Topic 4 (KPI reporting cadence) and the "naive RAG limits →
Phase 2 preview" discussion. Goes deep on the pipeline; **no new concepts
introduced**.

### What we do

Take the Day 1 pipeline (imported from `wk06_pipeline.py`), **vary every knob**,
then **construct queries designed to break it** and diagnose the failures.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1 | Import Day 1's pipeline from helper module | 3 min |
| 2 | Set up 5-question test set (with ideal-source markers, W5-style) | 5 min |
| **3** | **Knob 1 — Vary chunk size** (100 vs 200 vs 400) on all 5 questions | **12 min** |
| **4** | **Knob 2 — Vary K** (1, 3, 5, 7) on multi-fact query | **10 min** |
| 5 | Latency + cost at different K | 5 min |
| **6** | **Knob 3 — Vary embedding model** (3-small vs 3-large) | **12 min** |
| 7 | Cost calc: `3-small` vs `3-large` at scale | 5 min |
| **8** | **Knob 4 — Vary system prompt** (5 variants on one question) | **8 min** |
| 9 | Score every variant on all 5 questions (25 answers, eyeball-graded) | 10 min |
| **10-14** | **Construct 5 failure queries and diagnose each** | **18 min** |
| 15 | Wrap — what did we learn? | 2 min |

### The 5 failure queries (Cells 10-14)

Each is deliberately constructed to trigger a specific failure mode:

| Cell | Failure mode | What it exposes |
|---|---|---|
| 10 | **Ambiguous query** — "what temperature is used?" | Retrieval can't disambiguate between similar chunks |
| 11 | **Multi-fact question** — needs 2 different chunks | Top-K may not cover all facts |
| 12 | **Paraphrase drift** — 3 phrasings of same intent | Retrieval can be phrasing-fragile |
| 13 | **Adversarial query** — "ignore the context..." | Prompt injection defence |
| 14 | **Correct-sounding hallucination** — asks something not in corpus | Hardest to catch; answer LOOKS right |

For each: predict → run → diagnose. This is engineering-diagnostic muscle.

### What learners take away from Day 2

- **Chunk size, K, embedding model, system prompt** — each is a knob with real
  trade-offs. No universal setting.
- **Cost intuition** — output tokens are 4× more expensive than input at gpt-4o-mini
  pricing (ties back to W4 cost muscle).
- **Failure modes are predictable** — 5 constructions covered most of what
  will go wrong in production.
- **What W7-W11 will improve** — every failure they saw connects to a specific
  future week's fix.

### What stays out of scope in Day 2

Deliberately not covered (to avoid forward references):
- LLM-as-judge (W11 topic)
- Formal KPI dashboards (mentioned but not built)
- Golden set as a versioned artifact (W5 idea, applied conceptually)
- Reranking, hybrid search, query rewriting (W9)
- Caching, tombstones, lifecycle (W10)
- Vector DBs (W7)

Day 2 uses only W1-W6 concepts. The pipeline is Day 1. The trade-offs are W2/W4
cost thinking. The eyeball grading is W5. That's the entire palette.

---

## How the two days connect

- **Day 1** builds the pipeline as functions in the notebook
- **Day 2** imports the same functions from `wk06_pipeline.py` (a helper file
  that contains identical code — learners can open it and confirm)
- The **corpus is the same** across both days (10 hot-beverage documents)
- The **test questions in Day 2** are new but use the same corpus, so the
  answers are directly comparable across knob-variations

This mirrors real engineering: build once, exercise many times.

---

## When to stop and when to keep going

### Day 1
Stop when you've run all cells including 9d (partial-match failure). Keep going
if the class has time: try more queries in Cell 5.5, change K to 1 or 5 in
Cell 6.

### Day 2
Stop when you've completed at least 3 of the 5 failure diagnoses (Cells 10-14).
Keep going: construct your OWN failure query and try to predict which knob
would fix it.

---

## Next up: Track B

After both sessions, work through `AI-RAG_W6_Application_Growth_Guide.md`. That
takes the same pipeline and shows you how to add it to your capstone — new
files to add, few lines to modify in `main.py`, expected KPI numbers.

Total Track B time: ~2 to 2.5 hours self-paced.

---

## Troubleshooting

**Cell 1 fails: `AssertionError: Set OPENAI_API_KEY`**
Your environment doesn't have the key. In Vocareum: `export OPENAI_API_KEY=sk-...`
in the terminal before starting Jupyter.

**Day 2 Cell 1 fails: `ModuleNotFoundError: No module named 'wk06_pipeline'`**
The helper module isn't on your Python path. Make sure `wk06_pipeline.py` is
in the same directory as the notebook (i.e., `demos/`), and that you started
Jupyter from that directory (or added it to `sys.path`).

**Any cell fails: `RateLimitError`**
OpenAI quota. Wait a minute and retry. If persistent, lower `k` to reduce
prompt sizes or use a smaller test set.

**Cell 5 similarity scores look weird (all near zero, all near 1)**
Bug in `cosine`. Check division by norm.

**Day 2 Cell 3 — retrieval scores don't discriminate well**
Expected on a corpus this small. The point of Cell 3 isn't to find the perfect
chunk size — it's to see that chunk size affects retrieval systematically.

---

## What we intentionally did NOT do

For completeness, so you know what to look forward to:

- **No Qdrant / vector DB** — in-memory Python list. W7 replaces.
- **No embedding cache** — every rerun re-embeds. W7 adds.
- **No BM25 / keyword search** — pure dense retrieval. W9 adds hybrid.
- **No rerank** — trust top-K by cosine. W9 adds cross-encoder rerank.
- **No metadata filters** — can't restrict by source/date/type. W7 (Qdrant).
- **No LLM-as-judge** — eyeball grading only. W11 builds the framework.
- **No caching / lifecycle / tombstones** — W10.
- **No chunking beyond sliding window** — dumb but simple. W7 introduces structure-aware.

Every one will land in a subsequent week. What you built today is the skeleton.

---

*W6 Lab Guide, Track A. Companion to `wk06_day1_naive_rag_build.ipynb`,
`wk06_day2_pipeline_deep_dive.ipynb`, `wk06_pipeline.py`, and
`AI-RAG_W6_Application_Growth_Guide.md`.*
