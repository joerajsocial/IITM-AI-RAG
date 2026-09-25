# AI-RAG · Week 9 · Application Growth Guide

> **Take-home · self-paced · Core ~2.25 hours; Stretch optional ~45 min**
>
> **First Core + Stretch week.** Core is mandatory — everyone completes.
> Stretch is optional — only attempt if Core is solid.
>
> Track A (the two W9 notebooks) taught hybrid + rerank + query rewriting
> on a small 15-doc corpus. This guide walks you through applying the same
> pipeline to your capstone corpus and measuring the precision@k lift.

---

## Core + Stretch framing (new this week — read this)

**Core** (mandatory) is the deliverable this week's KPI snapshot depends on.
Steps 1-3 below are Core. Every learner completes these.

**Stretch** (optional) is depth for learners who finish Core with time and
energy to spare. Step 4 is Stretch. Do NOT attempt Stretch until Core is
solid — a broken Core plus attempted Stretch is worse than solid Core alone.

**Reason it works this way:** DANGER ZONE weeks stack cognitive load. Junior
learners protected from over-reaching; senior learners still get depth. Same
Friday deliverable, differentiated interior.

---

## What's changing this week

### Before W9 (end of W8 state)
- `capstone_chunks_v2` — Qdrant collection with 9-field metadata payload, PII scrubbed
- `src/rag/qdrant_rag.py` — pure **dense** retrieval (cosine over Qdrant)
- `wk8-snapshot.md` — precision baseline (retrieval hit rate, grounded response rate)

### After W9 Core
- `src/rag/retrieval.py` — new module with `hybrid_retrieve()` + `rerank()`
- `src/rag/qdrant_rag.py` — modified to use `retrieval.py`'s hybrid+rerank
- `docs/kpi/wk9-snapshot.md` — precision@3 and precision@5 delta vs W8
- `docs/wk9-precision-delta.md` — per-question comparison
- ADR extended with retrieval-stack decisions (BM25 library, RRF k, cross-encoder model)

### After W9 Stretch
- `src/rag/query_rewrite.py` — ONE query rewriting technique tried
- `docs/wk9-query-rewrite-trial.md` — findings + keep/drop decision

### Size of the Core change
- **1 new module** (`src/rag/retrieval.py`, ~140 lines)
- **1 file modified** (`src/rag/qdrant_rag.py`, ~10 lines)
- **2 new docs** (`wk9-precision-delta.md`, `wk9-snapshot.md`)
- **1 ADR extension**

---

## Prerequisites

- [ ] W8 complete: `capstone_chunks_v2` exists in Qdrant, wk8-snapshot.md committed
- [ ] Both W9 notebooks (Day 1 + Day 2) run cleanly
- [ ] Cross-encoder cached (from Day 1 homework)
- [ ] `rank-bm25` installed
- [ ] Capstone golden set at `data/golden_set.jsonl` (from W5)

Estimated cost: **negligible** — golden set is 20 questions; each retrieval
is ~$0.0001 in embedding cost + free BM25 + free local rerank. Total < $0.01.

---

# 🟢 CORE (mandatory)

## Core Step 1 (45 min) — Add `src/rag/retrieval.py`

Adapts the notebook demo to work over your `capstone_chunks_v2` collection.

Note: this module builds the BM25 index **at import time** by loading all
chunk texts from Qdrant. For a 100-300 chunk capstone that's ~2 seconds on
startup — negligible. Larger corpora would want to persist the BM25 index
to disk (see W10 caching topics).

```python
"""Hybrid retrieval + cross-encoder reranking for the capstone.

Replaces W8's pure-dense retrieval with:
  1. Hybrid retrieval (BM25 + Dense via RRF) - top-10
  2. Cross-encoder reranking - top-3

Public API:
  hybrid_retrieve(query, k=10) -> list[dict]
  rerank(query, candidates, top_k=3) -> list[dict]
  retrieve(query, k=3) -> list[dict]   # full stack, use this from qdrant_rag.py
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

from openai import OpenAI
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from src.rag.qdrant_store import _get_client, COLLECTION_NAME

# Cross-encoder lazy-init (heavy)
_reranker = None
def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker

_openai = None
def _get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI()
    return _openai


def simple_tokenize(text: str) -> list[str]:
    """Match W9 Day 1 tokenization: keeps hyphens/slashes in tokens.

    'AC-1042' stays as one token so BM25 can catch exact IDs.
    """
    return re.findall(r'[a-z0-9][a-z0-9\-/_]*', text.lower())


@lru_cache(maxsize=1)
def _load_bm25():
    """Load ALL chunks from Qdrant, build BM25 index over their text.
    
    Cached — pays the cost once per process. For very large corpora
    (>10K chunks), persist this to disk instead. That's a W10 topic.
    """
    client = _get_client()
    all_points = []
    offset = None
    while True:
        batch, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=200,
            offset=offset,
            with_payload=True,
        )
        all_points.extend(batch)
        if next_offset is None:
            break
        offset = next_offset
    
    # Preserve order — index positions map to point ids
    corpus_texts = [p.payload.get("text", "") for p in all_points]
    corpus_meta  = [{**p.payload, "point_id": p.id} for p in all_points]
    tokenized    = [simple_tokenize(t) for t in corpus_texts]
    return BM25Okapi(tokenized), corpus_meta


def bm25_search(query: str, k: int = 10) -> list[dict]:
    """BM25 retrieval — top-K by score. Returns list of dicts with 'point_id'."""
    bm25, meta = _load_bm25()
    scores = bm25.get_scores(simple_tokenize(query))
    ranked = sorted(zip(scores, meta), key=lambda p: p[0], reverse=True)
    return [
        {"id": str(m["point_id"]), "score": float(s), "doc": m}
        for s, m in ranked[:k]
    ]


def dense_search(query: str, k: int = 10) -> list[dict]:
    """Dense retrieval — Qdrant cosine top-K."""
    openai = _get_openai()
    client = _get_client()
    q_vec = openai.embeddings.create(
        model="text-embedding-3-small", input=[query]).data[0].embedding
    hits = client.query_points(
        collection_name=COLLECTION_NAME, query=q_vec, limit=k).points
    return [
        {"id": str(h.id), "score": h.score, "doc": {**h.payload, "point_id": h.id}}
        for h in hits
    ]


def rrf_fuse(ranked_lists: list[list[dict]], k: int = 60, top_n: int = 10) -> list[dict]:
    """Reciprocal Rank Fusion — same as W9 Day 1."""
    scores = {}
    docs = {}
    for ranked in ranked_lists:
        for rank, hit in enumerate(ranked, start=1):
            doc_id = hit["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in docs:
                docs[doc_id] = hit
    fused = sorted(scores.items(), key=lambda p: p[1], reverse=True)[:top_n]
    return [{**docs[doc_id], "rrf_score": s} for doc_id, s in fused]


def hybrid_retrieve(query: str, k_per_retriever: int = 10, k_final: int = 10) -> list[dict]:
    """BM25 + Dense + RRF combined."""
    bm25_hits  = bm25_search(query, k=k_per_retriever)
    dense_hits = dense_search(query, k=k_per_retriever)
    return rrf_fuse([bm25_hits, dense_hits], k=60, top_n=k_final)


def rerank(query: str, candidates: list[dict], top_k: int = 3) -> list[dict]:
    """Cross-encoder reranking — score (query, candidate.text) pairs."""
    reranker = _get_reranker()
    pairs = [(query, c["doc"].get("text", "")) for c in candidates]
    scores = reranker.predict(pairs)
    scored = [{**c, "rerank_score": float(s)} for c, s in zip(candidates, scores)]
    scored.sort(key=lambda h: h["rerank_score"], reverse=True)
    return scored[:top_k]


def retrieve(query: str, k: int = 3) -> list[dict]:
    """Full W9 stack: hybrid → rerank → top-k. Use this from qdrant_rag.py."""
    candidates = hybrid_retrieve(query, k_per_retriever=10, k_final=10)
    return rerank(query, candidates, top_k=k)
```

**Wire it into `qdrant_rag.py`** — change one import + one call:

```python
# In src/rag/qdrant_rag.py — REPLACE the old retrieval logic

from src.rag.retrieval import retrieve as retrieve_v9   # NEW

def ask_rag(question: str, k: int = 3) -> dict:
    # OLD (W8): retrieved = dense_retrieve(question, k=k)
    retrieved = retrieve_v9(question, k=k)               # NEW
    
    # ... rest of ask_rag unchanged (prompt build + LLM call)
```

**How to verify:**
```python
from src.rag.retrieval import retrieve
result = retrieve("what is the leave policy?", k=3)
for hit in result:
    print(f"  score={hit['rerank_score']:.3f}  {hit['doc'].get('chunk_id')}")
```

Should return 3 chunks with rerank scores — no crashes.

## Core Step 2 (45 min) — Run golden set + measure precision@k delta

Take your 20 golden-set questions from W5. Run them through the new
`retrieve()` function and compare against W8's baseline.

Create `scripts/measure_wk9_precision.py`:

```python
"""Measure precision@3 and precision@5 for the golden set.

Compares W9 (hybrid+rerank) vs W8 baseline (pure dense).
"""
import json
import sqlite3
from pathlib import Path

from src.rag.retrieval import retrieve, dense_search

GOLDEN_SET = Path("data/golden_set.jsonl")
DB_PATH = Path("results.db")

# Load golden set: {question, expected_chunk_ids: [...]}
golden = [json.loads(line) for line in GOLDEN_SET.read_text().splitlines() if line]
print(f"Loaded {len(golden)} golden questions.")

def precision_at_k(retrieved_ids, expected_ids, k):
    """1.0 if any expected chunk_id is in top-k retrieved; else 0.0.
    (Programme convention: single-answer questions; extend to multi-answer if needed.)"""
    top_k = retrieved_ids[:k]
    return 1.0 if any(eid in top_k for eid in expected_ids) else 0.0

def run_and_score(retriever_fn, label):
    p3_scores, p5_scores = [], []
    for q in golden:
        hits = retriever_fn(q["question"], k=5)
        retrieved_ids = [h["doc"].get("chunk_id") for h in hits]
        p3_scores.append(precision_at_k(retrieved_ids, q["expected_chunk_ids"], 3))
        p5_scores.append(precision_at_k(retrieved_ids, q["expected_chunk_ids"], 5))
    return {
        "label": label,
        "p_at_3": sum(p3_scores) / len(p3_scores),
        "p_at_5": sum(p5_scores) / len(p5_scores),
        "per_q_p3": p3_scores,
        "per_q_p5": p5_scores,
    }

# Baseline: pure dense (what W8 used)
baseline = run_and_score(lambda q, k: dense_search(q, k), "W8 dense-only")

# New: full W9 hybrid + rerank stack
v9 = run_and_score(retrieve, "W9 hybrid+rerank")

print(f"\n══ Precision comparison ══")
print(f"  {'Metric':<10s} {'W8 baseline':>12s} {'W9 hybrid+rerank':>18s} {'Delta':>10s}")
print(f"  {'------':<10s} {'-----------':>12s} {'-----------------':>18s} {'-----':>10s}")
for m in ["p_at_3", "p_at_5"]:
    delta = v9[m] - baseline[m]
    print(f"  {m:<10s} {baseline[m]:>12.3f} {v9[m]:>18.3f} {delta:>+10.3f}")

# Save per-question delta to docs/wk9-precision-delta.md
out = Path("docs/wk9-precision-delta.md")
lines = ["# W9 Precision Delta — per-question breakdown\n"]
lines.append(f"| Q# | Question | W8 P@3 | W9 P@3 | Change |")
lines.append(f"|---|---|---|---|---|")
for i, (q, p8_3, p9_3) in enumerate(zip(golden, baseline["per_q_p3"], v9["per_q_p3"])):
    change = "→ FIXED" if p9_3 > p8_3 else ("→ BROKE" if p9_3 < p8_3 else "same")
    lines.append(f"| {i+1} | {q['question'][:60]}... | {p8_3:.0f} | {p9_3:.0f} | {change} |")
out.write_text("\n".join(lines))
print(f"\nSaved per-question delta to {out}")
```

**Run it:**
```bash
python -m scripts.measure_wk9_precision
```

Expected: hybrid+rerank precision@3 beats dense-only by 5-20 percentage points.
If your delta is much smaller — likely tokenization issue upstream (see
troubleshooting). If your delta is much larger — congratulations, your corpus
really needed hybrid.

## Core Step 3 (45 min) — Update KPI snapshot + ADR

**Create `docs/kpi/wk9-snapshot.md`:**

```markdown
# wk9-snapshot.md — Hybrid retrieval + reranking baseline

**Date:** YYYY-MM-DD
**Retrieval stack:** BM25 (rank-bm25) + Dense (Qdrant cosine, text-embedding-3-small) via RRF (k=60) → Cross-encoder rerank (ms-marco-MiniLM-L-6-v2, top-3)

## Headline numbers

| Metric | W8 (dense-only) | W9 (hybrid+rerank) | Delta |
|---|---|---|---|
| Precision@3 | X.XX | Y.YY | +Z.ZZ |
| Precision@5 | X.XX | Y.YY | +Z.ZZ |
| Grounded response rate | X.XX | Y.YY | +Z.ZZ |
| Cost per query | $X.XX | $Y.YY | ≈ +$0.0001 (no new embed for rerank) |
| Latency p50 (ms) | XXX | YYY | +Z ms (mostly rerank CPU) |

## Method
- Same 20 golden-set questions from W5
- W8 numbers from wk8-snapshot.md
- W9 numbers from scripts/measure_wk9_precision.py (Cell 2 output)
- Grounded response rate: re-ran W4 judge on new retrievals

## What changed structurally
- W8 used pure dense retrieval; W9 adds BM25 + cross-encoder reranker
- Latency increased by ~150-200ms per query (mostly cross-encoder CPU)
- Cost per query essentially unchanged (rerank is local, not API)
- Precision@3 lifted from Y.YY to Z.ZZ — see docs/wk9-precision-delta.md for per-question

## Interpretation
[why did numbers move? which failure modes did hybrid fix? which did rerank fix?]
```

**Extend `docs/adr/0001-capstone-framing.md`** with a W9 section:

```markdown
## W9 — Hybrid retrieval + cross-encoder reranking

**Decision:** Capstone retrieval upgrades from pure dense to hybrid+rerank.

**Retrieval stack:**
- BM25 library: rank-bm25 (BM25Okapi)
- Tokenization: lowercase + alphanumeric-with-hyphens-and-slashes (preserves 'AC-1042', '/v2/dashboards')
- Dense model: text-embedding-3-small (1536 dim, unchanged from W7)
- Fusion: RRF with k=60 (Cormack 2009 default)
- Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2 (local CPU, ~80MB)
- Rerank input: top-10 from hybrid retrieve
- Rerank output: top-3 final

**Rejected alternatives:**
- Cohere Rerank API — paid ($1/1000 reranks), no meaningful accuracy lift on our corpus vs local cross-encoder
- Weighted score fusion (instead of RRF) — requires per-corpus weight tuning; RRF is tuning-free
- Larger cross-encoder (ms-marco-MiniLM-L-12-v2, ~120MB) — 2× slower for negligible accuracy lift on English enterprise docs
- LlamaIndex framework — retrieval fits comfortably in ~140 LOC; framework overhead not justified yet (revisit at W12+)

**Operational KPIs** (see docs/kpi/wk9-snapshot.md):
[fill in]

**Known gaps to revisit:**
- BM25 index rebuilt from Qdrant scroll at process start (~2s for 300 chunks). For larger corpora, persist to disk (W10 caching topic).
- Cross-encoder is CPU-bound; consider GPU or batch reranking if query volume grows.
```

---

# 🟡 STRETCH (optional, only if Core is solid)

## Stretch Step 4 (45 min) — Try ONE query rewriting technique

Pick ONE based on YOUR golden-set failure pattern:

| If your failing queries are... | Try... |
|---|---|
| Very short (2-4 words) | **HyDE** — fake answers are longer than queries, embed better |
| Ambiguous / could be phrased many ways | **Multi-query** — 3 rewrites capture variety |
| Specific/versioned but docs are general | **Step-back** — retrieve for the general version |

**Implement in `src/rag/query_rewrite.py`:**

```python
"""Query rewriting for the capstone — Stretch lab W9.

Pick ONE pattern based on your golden-set failure analysis.
"""
from openai import OpenAI
from src.rag.retrieval import dense_search, rrf_fuse

_openai = None
def _get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI()
    return _openai


# ── HyDE — pick this OR one of the others below ──

def hyde_retrieve(query: str, k: int = 3) -> list[dict]:
    """LLM drafts a fake answer; embed and retrieve using that."""
    openai = _get_openai()
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[{"role": "user", "content":
            f"Write a plausible one-paragraph answer to this question. Don't hedge.\n\n"
            f"Question: {query}\n\nHypothetical answer:"}],
    )
    hypothetical = resp.choices[0].message.content
    return dense_search(hypothetical, k=k)


# ── Multi-query — alternative ──

def multi_query_retrieve(query: str, k: int = 3, n_rewrites: int = 3) -> list[dict]:
    """LLM rewrites query N ways; retrieve for each; RRF-fuse the ranked lists."""
    openai = _get_openai()
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        messages=[{"role": "user", "content":
            f"Rewrite this question {n_rewrites} ways that return the same answer. "
            f"One per line, no numbering.\n\nQuestion: {query}"}],
    )
    rewrites = [r.strip() for r in resp.choices[0].message.content.split("\n") if r.strip()]
    all_queries = [query] + rewrites[:n_rewrites]
    ranked_lists = [dense_search(q, k=5) for q in all_queries]
    return rrf_fuse(ranked_lists, k=60, top_n=k)


# ── Step-back — alternative ──

def step_back_retrieve(query: str, k: int = 3) -> list[dict]:
    """LLM generates a more general version; retrieve for both; fuse."""
    openai = _get_openai()
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content":
            f"Given a specific question, write a more general version that would "
            f"return the background needed to answer the specific question. Return only "
            f"the general question.\n\nSpecific: {query}\nGeneral:"}],
    )
    general = resp.choices[0].message.content.strip()
    ranked_lists = [dense_search(query, k=5), dense_search(general, k=5)]
    return rrf_fuse(ranked_lists, k=60, top_n=k)
```

Add to `scripts/measure_wk9_precision.py` a third run:
```python
from src.rag.query_rewrite import hyde_retrieve  # or multi_query_retrieve, etc.
stretch = run_and_score(hyde_retrieve, "W9 + HyDE stretch")
# ... print alongside baseline and v9
```

**Verdict doc — `docs/wk9-query-rewrite-trial.md`:**

```markdown
# W9 Stretch — Query rewriting trial

**Technique tried:** [HyDE / Multi-query / Step-back]
**Reason for choice:** [what failure pattern in your golden set motivated this?]

## Results

| Metric | Core (hybrid+rerank) | + Rewriting | Delta |
|---|---|---|---|
| Precision@3 | X.XX | Y.YY | +/-Z.ZZ |
| Cost per query | $X.XX | $Y.YY | +$0.0001 (LLM rewrite call) |
| Latency p50 | XXX ms | YYY ms | +Z ms (LLM rewrite call) |

## Verdict

[ ] KEEP — precision lift justifies cost/latency
[ ] DROP — no meaningful improvement, not worth the extra LLM call
[ ] KEEP BUT CONDITIONAL — only apply for [specific query pattern]

## Reasoning
[be specific — which queries improved? which got worse? what's the pattern?]
```

**Common Stretch reality:** on well-tuned corpora, query rewriting adds ≤2 pp
lift and doubles latency. On corpora with obvious query-language mismatch
(user says "cost", docs say "pricing"), you may see 5-10 pp lift. Either
result is valid — the point is having a real decision, not a "tried it."

---

## Testing checklist

Before W9 is done:

### Core
- [ ] `src/rag/retrieval.py` exists; `retrieve("test query", k=3)` returns 3 results
- [ ] `qdrant_rag.py` wired to use `retrieval.retrieve()`
- [ ] `docs/kpi/wk9-snapshot.md` shows precision@3 and precision@5 vs W8 baseline
- [ ] `docs/wk9-precision-delta.md` per-question comparison committed
- [ ] ADR extended with W9 retrieval-stack decisions

### Stretch (if attempted)
- [ ] `src/rag/query_rewrite.py` implements ONE technique
- [ ] `docs/wk9-query-rewrite-trial.md` with clear KEEP/DROP verdict

---

## Common issues + fixes

**BM25 tokenization eats my error codes**
Check `simple_tokenize("AC-1042")` returns `['ac-1042']` not `['ac', '1042']`.
If wrong, the regex is stripping hyphens. Use the pattern from `retrieval.py`
exactly.

**Precision@3 DROPPED from W8 to W9 (rare but happens)**
Debug:
1. Check `hybrid_retrieve` returns sensible top-10 for 3 golden questions manually
2. Check rerank scores are non-uniform (if all scores are ~0, model didn't load)
3. Check `chunk_id` field is present in payload for every point (that's what matches expected_chunk_ids)
4. If you're on a chat/blog corpus (all natural language, no proper nouns), the hybrid+rerank lift may be genuinely small. That's a valid finding — document it in wk9-snapshot.md.

**Reranker load hangs for 60+ seconds**
First-run only; downloads ~80MB from HuggingFace. If it keeps hanging on
subsequent runs, delete `~/.cache/huggingface/hub/` and re-trigger the download.

**BM25 rebuild takes >30 seconds on my capstone**
Your corpus is bigger than typical for the programme. The `_load_bm25()`
function scrolls all points from Qdrant. For 10K+ chunks, persist the
tokenized corpus to a pickle file. W10 caching topics cover this.

**LlamaIndex looks tempting; should I switch now?**
Not yet. Stay from-scratch through at least W12. When you migrate, W9's
`retrieval.py` maps cleanly onto LlamaIndex's `QueryFusionRetriever +
SentenceTransformerRerank`. The refactor is <100 lines.

---

## What you should have when done

**Core (mandatory):**
- `src/rag/retrieval.py` (new, ~140 lines)
- `src/rag/qdrant_rag.py` (modified, ~10 lines)
- `scripts/measure_wk9_precision.py` (new)
- `docs/kpi/wk9-snapshot.md` (new)
- `docs/wk9-precision-delta.md` (new)
- `docs/adr/0001-capstone-framing.md` (W9 section added)

**Stretch (optional):**
- `src/rag/query_rewrite.py` (new)
- `docs/wk9-query-rewrite-trial.md` (new)

**Preserved:**
- `capstone_chunks_v2` collection — unchanged (retrieval is code-side, not data-side)
- `naive_rag.py` from W6, `qdrant_store.py` from W7 — unchanged

**Total time:** Core ~2.25 hours; Stretch ~45 min. Longer if you hit
tokenization or download issues.

---

## What's coming in W10

**Back to normal pace.** W10 is RAG Optimization + KB Lifecycle:
- Caching (embedding cache, retrieval cache, LLM response cache)
- Evaluation harness (pytest for retrieval; regression testing)
- KB updates (adding/deleting chunks without full reingest)
- Cost + latency instrumentation

W9's `hybrid_retrieve()` and `rerank()` become caching targets in W10. Your
`retrieval.py` module gets small additions, not rewrites.

The hard concept peaks are behind you until W13-W14 (agents). Consolidate
this weekend — re-read your ADR, look at wk9-precision-delta.md, understand
WHY each fixed query got fixed.

---

*W9 Application Growth Guide. First Core+Stretch week. Track B of the
two-track W9 pattern. Companion to `wk09_day1_hybrid_search.ipynb`,
`wk09_day2_rerank_rewrite.ipynb`, `wk09_pipeline.py`, and
`AI-RAG_W9_Lab_Guide.md`.*
