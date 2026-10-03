"""MP2 · Mini-RAG — Starter Template
====================================

You'll build a complete RAG pipeline over the Sherlock Holmes corpus in this
file. Fill in every TODO. The reference solution is ~250 lines, but yours can
be shorter or longer — what matters is that it works end-to-end.

Pipeline you're building:
    corpus/*.txt  →  chunks  →  embeddings  →  Qdrant
                                                  ↓
                              question  →  retrieve  →  answer + citations

Run sequence (once you've filled in the TODOs):
    pip install -r requirements.txt
    source .env                 # exports your OpenAI + Qdrant credentials
    python mp2_rag.py ingest    # builds the collection (run once)
    python mp2_rag.py ask       # interactive Q&A loop
    python mp2_rag.py validate  # runs against data/predefined_questions.jsonl

Tip: get the CORE pipeline working FIRST (Steps 1-7 below), THEN come back to
polish and add your 3 questions. Don't try to perfect each step before moving
on — you'll learn more from a rough end-to-end loop than a polished half.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
import asyncio
from pathlib import Path
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.src.rag_pipeline import (
    chunk_documents, chunk_text, build_index, embed_batch,
    retrieve, ask_rag,
    cost_usd, DEFAULT_SYSTEM,
    calc_golden_hit_cost_lat, dense_search,
    create_collection, upsert_collection, retrive_from_collection, fetch_all_chunks_from_qdrant, 
    simple_tokenize, build_bm25_index, bm25_search,
    rrf_fuse, rerank, load_reranker, 
)

from rag.src.rag_settings import Settings, RunSummary


# ─── Configuration ──────────────────────────────────────────────────────

CORPUS_DIR        = Path(__file__).parent / "corpus"
DATA_DIR          = Path(__file__).parent / "data"
COLLECTION_NAME   = "mp2_sherlock"
EMBEDDING_MODEL   = "text-embedding-3-small"
EMBEDDING_DIM     = 1536
CHAT_MODEL        = "gpt-4o-mini"
TARGET_CHUNK_SIZE = 500   # characters
CHUNK_OVERLAP     = 80    # characters

# rag pipeline GVs
coll_name = COLLECTION_NAME
CHUNK_SIZE = TARGET_CHUNK_SIZE
OVERLAP = CHUNK_OVERLAP

rerank_required = False

#openai = OpenAI()
#qdrant = QdrantClient(
#    url=os.environ["QDRANT_URL"],
#    api_key=os.environ.get("QDRANT_API_KEY"),
#)
# ─── Step 1: Load the corpus ────────────────────────────────────────────

def load_corpus(corpus_dir: Path) -> list[dict[str, Any]]:
    all_content = []
    file_names_list = []
    # 2. Loop through files (e.g., all text files)
    #try:
    print(CORPUS_DIR, corpus_dir)
    for file_path in CORPUS_DIR.glob("*.txt"):
        if file_path.is_file():  # Ensure it is a file, not a subfolder
            print(f"--- Reading: {file_path.name} ---")
            file_names_list.append(file_path.name)
            # 3. Open and read the file safely
            with open(file_path, mode="r", encoding="utf-8") as file:
                    content = file.read()
                    all_content.append({
                        "id": file_path.name.replace("../",""), "text": content})
    print("Finished")
    print(f"Files: {len(file_names_list)} \n{file_names_list}")

    #    raise NotImplementedError("Implement load_corpus")
    return all_content


# ─── Step 7: Generate the answer ────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant answering questions about a small
collection of Sherlock Holmes stories. You will be given the user's question and
several relevant excerpts. Use ONLY the provided excerpts to answer. If the
excerpts don't contain the answer, say so plainly. Cite the source (story title
+ section) in your answer."""


async def answer(question: str, k: int = 3) -> dict[str, Any]:
    """End-to-end: retrieve, format context, call LLM, return result.

    TODO:
      - Call retrieve(question, k=k)
      - Format the retrieved chunks into a context string
        (include "[Source: <title> — <section>]" before each)
      - Call openai.chat.completions.create with SYSTEM_PROMPT and the user message
      - Return dict with: question, answer, citations, latency_ms
    """
    # TODO: your code here
    print(f"Rerank required?: {rerank_required}")
    question_list = []
    question_list.append(question)
    all_chunks = fetch_all_chunks_from_qdrant(coll_name)
    bm25_corpus = build_bm25_index(all_chunks)
# ─── Step 6: Retrieve ───────────────────────────────────────────────────
# ─── Step 6 ==> Dense search, BM25, Cross encoder
    dense_results, bm25_result = await asyncio.gather(
        dense_search(question, coll_name, k),
        bm25_search(question, bm25_corpus, all_chunks, k),
    )
    rrk_k = 5
    rerank_k = 3
    rrf_result = rrf_fuse([dense_results, bm25_result], k=60, top_n=rrk_k)
    rerank_result = ( rerank(question, rrf_result, rerank_k) 
            if str(rerank_required).strip().lower() in ["true", "yes", "y", "1"]  else rrf_result)
    responses = await ask_rag(question, rerank_result, k, system=SYSTEM_PROMPT)
    #print(responses)
    return responses

# ─── Validation harness (provided — do not modify) ──────────────────────

def validate_against(jsonl_path: Path) -> None:
    questions = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
    print(f"\n  Validating {len(questions)} questions from {jsonl_path.name}…\n")

    hits = 0
    total_chunk_hits= 0
    for q in questions:
        result = asyncio.run(answer(q["question"], k=7))
        #print("==============================")
        #print(result)
        (cited_sources, cited_chunkid) = map(set, zip(*[(cit.get('source_id'), cit.get('chunk_id')) for cit in result['retrieved']])) 
        #{(cit.get('source_id'), cit.get('chunk_id')) for cit in result['retrieved']}
        source_hit = q["expected_source"] in cited_sources
        ##chunk_hit = q["expected_chunk_id"] in cited_chunkid
        expected_set = set(q["expected_chunk_id"]) if isinstance(q["expected_chunk_id"], list) else {q["expected_chunk_id"]}

        # True only if ALL expected chunks were retrieved
        chunk_hit = expected_set.issubset(cited_chunkid)

        ans_lower = result["answer"].lower()
        facts_hit = sum(1 for fact in q.get("expected_facts", []) if fact.lower() in ans_lower)
        facts_total = len(q.get("expected_facts", []))

        verdict = "✓" if source_hit else "✗"
        verdict = verdict + ("✓" if chunk_hit else "✗")
        print(f"  {verdict} {q['id']}")
        print(f"      Q: {q['question']}")
        print(f"      Cited: {', '.join(cited_sources)} | Chunks: {cited_chunkid}")
        print(f"      Expected: {q['expected_source']} | Expected chunks: {q['expected_chunk_id']}")
        print(f"      Facts matched: {facts_hit}/{facts_total}")
        print(f"      Latency: {result.get('latency_s', '?')}s")
        print(f"      Answer: {result.get('answer', '')}\n      Expected ans: {q['expected_facts']}")
        print()
        if source_hit:
            hits += 1
        if chunk_hit:
            total_chunk_hits += 1
    print(f"  Source-match: {hits}/{len(questions)}\n  Chunk-match {total_chunk_hits}/{len(questions)}")


# ─── CLI (provided — do not modify) ─────────────────────────────────────

def cmd_ingest() -> None:
    print("→ Loading corpus…")
    docs = load_corpus(CORPUS_DIR)
    #print(docs)
    print(f"  {len(docs)} documents loaded")

    print("→ Chunking…")
    all_chunks: list[dict[str, Any]] = []

# ─── Step 2: Chunk each document ────────────────────────────────────────
    all_chunks = chunk_documents(docs, size = CHUNK_SIZE, overlap = OVERLAP)
    #print(all_chunks)
    print(f"→ Total chunks: {len(all_chunks)}")
    print("→ Setting up Qdrant collection…")
    print("→ Ingesting…")
# ─── Step 3: Embed text ─────────────────────────────────────────────────
    index = build_index(all_chunks)
# ─── Step 4: Set up the Qdrant collection ───────────────────────────────
    create_collection(coll_name)
# ─── Step 5: Ingest chunks into Qdrant ──────────────────────────────────
    upsert_collection(coll_name, index)
    print("\n✓ Done. Try: python mp2_rag.py ask")


def cmd_ask() -> None:
    global rerank_required
    try:
        rerank_required = input(f"Rerank required?: {rerank_required}").strip()
    except (EOFError, KeyboardInterrupt):
            print()
            return
    print("Mini-RAG over the Sherlock Holmes corpus.")
    print("Type your question. Empty line or Ctrl-C to exit.\n")
    while True:
        try:
            q = input("? ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not q:
            return
        result = asyncio.run(answer(q, k=7))
        print(f"\n{result['answer']}\n")
        print(f"  Sources: {result['sources']}")
        #for c in result["citations"]:
        #    print(f"    - {c['title']} — {c['section']}")
        #print(result['sources'])
        total_cost = cost_usd(result['tokens_in'], result['tokens_out'])
        print(f"  Latency: {result.get('latency_s', '?')}s\n")
        print(f"  Cost: ${total_cost}")


def cmd_validate() -> None:
    global rerank_required
    try:
        rerank_required = input(f"Rerank required?: {rerank_required}").strip()
    except (EOFError, KeyboardInterrupt):
            print()
            return
    validate_against(DATA_DIR / "predefined_questions.jsonl")
    learner_path = DATA_DIR / "learner_questions.jsonl"
    if learner_path.exists():
        first = json.loads(learner_path.read_text().splitlines()[0])
        if not first["question"].startswith("Replace this"):
            validate_against(learner_path)

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "ingest":   cmd_ingest()
    elif cmd == "ask":    cmd_ask()
    elif cmd == "validate": cmd_validate()
    else:
        print(f"Unknown command: {cmd}\n")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
