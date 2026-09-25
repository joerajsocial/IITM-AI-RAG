# AI-RAG · Week 9 · Lab Guide
## Advanced Retrieval — Hybrid Search + Rerank + Query Rewriting

> **⚠ DANGER ZONE week.** Two in-session notebooks · standalone Jupyter · Track A.
>
> **Day 1 (75 min):** Naive-RAG failures + BM25 + RRF + hybrid retrieval.
> **Day 2 (90 min):** Cross-encoder reranker + query rewriting (HyDE + multi-query) + LlamaIndex intro.
>
> **First Core + Stretch lab week.** Track B distinguishes CORE (mandatory) from STRETCH (optional). Notebooks cover the same content in class for everyone; the take-home split is where the tagging matters.
>
> Both notebooks use a bundled 15-doc "Acme Analytics Platform" corpus designed to expose the tension between BM25 and dense retrieval.

---

## DANGER ZONE — what this means for delivery

W9 is flagged as the **first difficulty spike** per the difficulty heatmap. Three new ideas stack (BM25, RRF, cross-encoders) plus two query rewriting patterns. If you rush, learners hit W10 confused and it compounds.

**Concrete adaptations built into this week:**
- Live hands-on **split into two blocks** (~25 min each) instead of one long one — one in Day 1, one in Day 2
- **Slow down on Cell 2 of Day 1** — the failure demo is where the "why are we doing this" case is made. Do not skip discussion.
- **Cross-encoder pre-download is Day 1 homework** — a 80MB download during the Day 2 live session kills the pace
- **Pair junior with senior** for both hands-on blocks (proactive, not reactive)
- Better to drop the LlamaIndex intro to 5 min than skip the rerank hands-on

---

## Package contents

Inside `demos/`:

| File | Session | Purpose |
|---|---|---|
| `wk09_day1_hybrid_search.ipynb` | Day 1 (75 min) | Failures + BM25 + RRF + hybrid |
| `wk09_day2_rerank_rewrite.ipynb` | Day 2 (90 min) | Rerank + query rewriting + LlamaIndex |
| `wk09_pipeline.py` | Helper | Shared corpus + BM25 + RRF + reranker functions Day 2 imports |
| `generate_acme_corpus.py` | Setup | Regenerates the 15-doc corpus + 6 test queries |
| `sample_docs/acme_docs.jsonl` | Sample | 15 docs (features, error codes, pricing, API endpoints) |
| `sample_docs/acme_test_queries.jsonl` | Sample | 6 queries with expected-winner annotations |

**Want more variety?** Two options:
1. Modify `generate_acme_corpus.py` — add more docs to the CORPUS list, more queries to TEST_QUERIES
2. Substitute your own JSONL with the same schema: `{"id": str, "title": str, "text": str, "category": str}`

---

## Prerequisites

### Day 1
- [ ] Vocareum notebook environment
- [ ] `pip install openai qdrant-client rank-bm25 numpy`
- [ ] `OPENAI_API_KEY` set (for dense embeddings)
- [ ] `QDRANT_URL` + `QDRANT_API_KEY` set (from W7)
- [ ] Corpus generated: `python demos/generate_acme_corpus.py`

### Day 2 (additional)
- [ ] `pip install sentence-transformers` **(Day 1 homework — 80MB model download)**
- [ ] `CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')` cached (Day 1 homework — verify with a scoring call)

**Cost across both notebooks: ~$0.02** in OpenAI credits. Cross-encoder is free (local CPU). Qdrant free tier.

---

## Day 1 · `wk09_day1_hybrid_search.ipynb` (75 min)

Aligned to deck slides 4-20 — Topic 1 (Failures) + Topic 2 (Hybrid + BM25 + RRF) + Block 1 hands-on.

### What we do

Name the naive-RAG failure modes explicitly, meet BM25, learn RRF, build `hybrid_retrieve()`. Uses the 15-doc Acme corpus which is designed to make BM25/dense differences visible.

### Section-by-section walkthrough (75 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup + load corpus + test queries with annotations | 3 min |
| **2** | **Dense-only failure demo** — 6 queries against Qdrant; 2 fail on exact-match questions | **12 min** |
| 3 | Failure taxonomy — 4 modes → 4 upgrades | 5 min |
| **4** | **BM25 fundamentals** — TF + IDF + length norm; why not raw TF-IDF | **10 min** |
| **5** | **BM25 in code** — tokenization sanity check + fit + run same 6 queries | **10 min** |
| **6** | **Neither dominates** — side-by-side comparison table (Dense vs BM25) | **10 min** |
| **7** | **RRF (Reciprocal Rank Fusion)** — the formula, why k=60, worked example | **10 min** |
| **8** | **Hybrid in code** — combine BM25 + Dense + RRF; run 6 queries; see the lift | **10 min** |
| 9 | Wrap + Day 2 homework (cross-encoder pre-download) | 5 min |

**Bold cells are the pedagogical peaks.**

### Discussion moments built into the notebook

- **Cell 2 (the dense-only failure demo):** count which queries fail, why. This is where the case for hybrid is made. Do not rush.
- **Cell 5:** on the AC-1042 query, BM25 may return `err_ac4408` (cross-references AC-1042) instead of `err_ac1042`. Real docs cross-reference — BM25 alone can't distinguish "about" from "mentions." This is a great teaching moment about BM25's limitations even on its home turf.
- **Cell 6:** count the "only dense right" + "only BM25 right" rows. That's the population where hybrid gives you what neither alone gets.
- **Cell 8:** did hybrid ≥ max(dense, BM25) on the 6 queries? On this small corpus with cross-references, hybrid may not be perfect — that's where the reranker (Day 2) earns its keep.

### What learners take away from Day 1

1. Working `hybrid_retrieve()` function combining BM25 + Dense + RRF
2. Clear intuition for when BM25 wins vs when dense wins
3. Understanding of RRF math (rank-based fusion, k=60 constant)
4. Confidence to wire this into their capstone (Track B Core Step 1)

### What Day 1 does NOT do

- Cross-encoder rerankers (Day 2)
- Query rewriting (Day 2 conceptually; Stretch lab to try)
- LlamaIndex (Day 2)
- Anything capstone-related (Track B)
- Precision@k measurement (Track B Core Step 2)

---

## Day 2 · `wk09_day2_rerank_rewrite.ipynb` (90 min)

Aligned to deck slides 21-42 — Topic 3 (Rerankers) + Block 2 hands-on + Topic 4 (Query Rewriting) + Topic 5 (LlamaIndex).

### What we do

Add the second stage that turns "top-10 with rough order" into "top-3 with precise order." Cover query rewriting patterns (HyDE runnable, multi-query runnable, step-back sketch). Close with a 20-line LlamaIndex equivalent of what we built, with even-handed framing.

### Section-by-section walkthrough (90 min)

| Cells | What | Time |
|---|---|---|
| 1 | Setup + **HARD assertion cross-encoder cached** (yesterday's homework) | 5 min |
| **2** | **Two-stage retrieval concept** — recall wide (k=10) then precision narrow (k=3) | **8 min** |
| **3** | **Bi-encoder vs cross-encoder** — architecture; why cross is slow but accurate | **10 min** |
| **4** | **Rerank in code** — CrossEncoder + `rerank(query, candidates)` function | **10 min** |
| **5** | **Full stack in action** — hybrid → rerank; compare vs Day 1 hybrid-only | **12 min** |
| **6** | **Latency budget** — time each stage over 3 runs; sizing k_candidates | **8 min** |
| **7** | **HyDE (runnable)** — LLM drafts fake answer → embed → retrieve | **10 min** |
| **8** | **Multi-query (runnable)** — LLM rewrites 3 ways → RRF-fuse | **8 min** |
| 9 | Step-back (verbal + code sketch, not run) | 5 min |
| **10** | **LlamaIndex 20-line equivalent** — even-handed framing | **8 min** |
| 11 | Cleanup + wrap + Core/Stretch hand-off | 6 min |

**Bold cells are the pedagogical peaks.**

### Discussion moments built into the notebook

- **Cell 1:** if the cross-encoder isn't cached, the notebook stops. Loud fail is better than a silent 80MB download mid-session.
- **Cell 4:** on the AC-1042 sanity check, does the reranker score `err_ac1042` higher than `err_ac4408`? It should — cross-encoders read the (query, doc) pair together and can distinguish "about" from "mentions."
- **Cell 5:** which queries did the reranker fix that hybrid missed? Which queries are STILL wrong after rerank (candidates for query rewriting)?
- **Cell 6 (latency budget):** notice reranker dominates the timing. Discussion: at your capstone scale (100-300 chunks retrieved down to top-10), is 150ms acceptable? For a chat interface, yes. For a bulk-processing job, maybe optimize.
- **Cell 8 (multi-query):** cost warning — 4× retrievals per user query. Do you have the query volume budget for this?
- **Cell 10 (LlamaIndex):** even-handed framing. Not "frameworks are for beginners" nor "frameworks are magic." Taste-and-scale decision.

### What learners take away from Day 2

- Working `rerank()` on top of `hybrid_retrieve()` = full W9 retrieval stack
- Concrete latency budget for the pipeline (embed + BM25 + dense + RRF + rerank)
- Ability to try HyDE / multi-query on their capstone (Stretch)
- Framework fluency without adoption pressure

### What Day 2 does NOT do

- Learner's capstone (Track B Core)
- Precision@k measurement on golden set (Track B Core Step 2)
- Step-back runnable code (only sketch — Stretch lab option)
- Cohere Rerank API (mentioned in lesson plan, not covered — local cross-encoder does the job)
- Actually switching to LlamaIndex (framing only; no adoption this week)

---

## How the two days connect

- **Day 1** builds BM25 + RRF cell-by-cell in the notebook
- **Day 2** imports those functions from `wk09_pipeline.py` (same code)
- The **corpus is shared** across both days
- Day 2 Cell 5 (full stack) explicitly compares against Day 1's hybrid-only numbers — teaches the incremental value of each stage

---

## Track B: First Core + Stretch week (new pedagogical pattern)

**This is the first week we distinguish Core (mandatory) from Stretch (optional).**
The distinction continues for the rest of the programme.

**How to frame it to learners:**
> "Core is the deliverable everyone commits. Stretch is for learners who finish Core fast or want depth. **Don't attempt Stretch until Core is solid.** If your Core precision@k didn't improve, that's the debugging priority — not Stretch."

**Common misuse to head off:**
- Learners attempting Stretch (query rewriting) before Core is done, then having neither working by end-of-week
- Learners skipping Stretch because they think Core is "just the basics" — Core here is a genuine architectural upgrade

---

## When to stop and when to keep going

### Day 1
Stop when hybrid_retrieve returns sensible top-1 for all 6 queries (Cell 8). Keep going: try `k=1` for hybrid and see how bad it is; try `k=15` and see the rerank latency implication for tomorrow.

### Day 2
Stop when Cell 5 shows the full stack lifting precision vs hybrid-only. Keep going: modify Cell 5 to also compute mean reciprocal rank (MRR) — it's a more sensitive metric than top-1 accuracy.

---

## Troubleshooting

**Cell 1 (Day 1) fails: `AssertionError: Missing sample_docs/acme_docs.jsonl`**
Run `python demos/generate_acme_corpus.py` from your notebook working directory.

**Cell 5 (Day 1) — BM25 gets the AC-1042 query wrong (returns err_ac4408)**
This is expected on our corpus. `err_ac4408` cross-references AC-1042 in its "see AC-1042" note. BM25 matches both docs on the token `ac-1042` and can pick the wrong one when the query is short. Use this live as a teaching moment for BM25's limitations. It gets fixed by the cross-encoder in Day 2 Cell 5.

**Cell 1 (Day 2) fails: `ImportError: SENTENCE-TRANSFORMERS NOT INSTALLED`**
You skipped yesterday's homework. Run:
```
pip install sentence-transformers
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```
Then **restart the kernel** and re-run.

**Cell 1 (Day 2) fails: `RuntimeError: Cross-encoder model failed to load`**
The model failed to download. Common causes:
1. Corporate network blocks huggingface.co
2. Vocareum has intermittent HuggingFace access
Try: `export HF_HUB_DOWNLOAD_TIMEOUT=60` and retry the CrossEncoder call. If still failing, tell your instructor — Cohere Rerank API is a paid alternative.

**Day 2 Cell 6 timings look wildly different from Vocareum-to-Vocareum**
Vocareum shares CPU. Timing is noisy. What matters is the RELATIVE proportions (reranker dominates) — the absolute numbers vary 2-5×.

**Rerank breaks a query that hybrid got right (rare but possible)**
Cross-encoders aren't perfect. If this happens on your 6-query test set, note it — a real signal that your corpus has adversarial content for the reranker's training distribution. Rare on English enterprise docs.

**Cell 7 (HyDE) — hypothetical answer looks nothing like your corpus**
The LLM was asked to be plausible, not accurate. That's the trick — HyDE works because "shape of an answer" is embedding-close to real answers, even if the content is wrong.

**Cell 8 (Multi-query) — rewrites are basically the same sentence**
Increase temperature in the rewrite call from 0.4 to 0.7 or 0.8. Also try `n_rewrites=5` and take the most-different 3.

---

## What we intentionally did NOT do

- **Cohere Rerank API** — mentioned in lesson plan, not covered. Local cross-encoder gives the same lesson without an API key. Learners can swap for Cohere in Stretch if they want.
- **Step-back runnable** — sketch only. Learners implement it in Stretch if they pick step-back.
- **LlamaIndex adoption** — framing only, not switching. The programme stays from-scratch through at least W12.
- **BM25F, BM25L, or other BM25 variants** — BM25Okapi is the industry default. Others are corpus-specific optimizations.
- **Learned sparse retrievers (SPLADE, ColBERT)** — advanced topic. Optional Stretch reading if interested.

---

*W9 Lab Guide, Track A. Companion to `wk09_day1_hybrid_search.ipynb`,
`wk09_day2_rerank_rewrite.ipynb`, `wk09_pipeline.py`, and
`AI-RAG_W9_Application_Growth_Guide.md`.*
