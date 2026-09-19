"""wk06_pipeline.py — the naive RAG pipeline built in Day 1.

Day 2 imports these functions so we don't spend 20 minutes rebuilding.
The code here is IDENTICAL to what Day 1 constructs cell-by-cell —
learners can read this file and see the whole pipeline in one place.

Pure functions. No frameworks. ~80 lines.
"""
from __future__ import annotations

import os
import numpy as np
from openai import OpenAI
import time
import asyncio

#logging and settings
## - to implement ==>> from .logging_config import get_logger
from .rag_settings import Settings, RunSummary

assert os.environ.get("OPENAI_API_KEY"), "Set OPENAI_API_KEY before importing"

_rag_settings = Settings()

EMBED_MODEL = _rag_settings.EMBED_MODEL
CHAT_MODEL = _rag_settings.CHAT_MODEL


_client = OpenAI()

# ─── Chunking ────────────────────────────────────────────────────────

def chunk_text(text: str, size: int = 200, overlap: int = 40) -> list[str]:
    """Sliding window over characters. Simplest possible chunker."""
    if len(text) <= size:
        return [text]
    chunks, i = [], 0
    while i < len(text):
        end = min(i + size, len(text))
        chunks.append(text[i:end])
        if end == len(text):
            break
        i = end - overlap
    return chunks


def chunk_documents(documents: list[dict], size: int = 200,
                    overlap: int = 40) -> list[dict]:
    """Chunk every document. Returns flat list with source pointers."""
    all_chunks = []
    for doc in documents:
        for chunk_idx, chunk in enumerate(chunk_text(doc["text"], size, overlap)):
            all_chunks.append({
                "chunk_id":  f"{doc['id']}#{chunk_idx}",
                "source_id": doc["id"],
                "text":      chunk,
            })
    return all_chunks


# ─── Embedding ───────────────────────────────────────────────────────

def embed_batch(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """One API call, list of vectors back."""
    resp = _client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def build_index(chunks: list[dict], model: str = EMBED_MODEL) -> list[dict]:
    """Attach 'vector' field to each chunk. Returns the same list mutated."""
    texts = [c["text"] for c in chunks]
    vectors = embed_batch(texts, model=model)
    for chunk, vec in zip(chunks, vectors):
        chunk["vector"] = vec
    return chunks


# ─── Similarity + retrieval ──────────────────────────────────────────

def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


def retrieve(query: str, index: list[dict], k: int = 3,
             embed_model: str = EMBED_MODEL) -> list[dict]:
    """Embed the query, rank chunks by cosine, return top-K with scores."""
    q_vec = embed_batch([query], model=embed_model)[0]
    scored = [(cosine(q_vec, c["vector"]), c) for c in index]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [{**c, "score": s} for s, c in scored[:k]]


# ─── Prompt + generate ───────────────────────────────────────────────

DEFAULT_SYSTEM = (
    "You are a helpful assistant. Answer the user's question using ONLY the "
    "provided context. If the context does not contain the answer, say so "
    "plainly. Cite the source id in square brackets after any fact you use."
)


def build_prompt(question: str, retrieved: list[dict],
                 system: str = DEFAULT_SYSTEM) -> tuple[str, str]:
    """Return (system_message, user_message) so we can inspect them."""
    context = "\n\n".join(
        f"[{hit['chunk_id']}]\n{hit['text']}"
        for hit in retrieved
    )
    user_msg = f"Context:\n{context}\n\n---\n\nQuestion: {question}"
    return system, user_msg


async def ask_rag(question: str, index: list[dict], k: int = 3,
            system: str = DEFAULT_SYSTEM,
            embed_model: str = EMBED_MODEL,
            chat_model: str = CHAT_MODEL) -> dict:
    """Full pipeline: retrieve → prompt → generate. Returns dict with
    answer, sources, cost, latency-relevant token counts."""
    if _rag_settings.RETRIVE_FROM_COLLECTION:
        retrieved = index
    else: 
        retrieved = retrieve(question, index, k=k, embed_model=embed_model)
    start_time = time.perf_counter()
    # Augmentation and generation only if generation is True
    if _rag_settings.GENERATE_ANSWER_RAG:
        system_msg, user_msg = build_prompt(question, retrieved, system=system)
        resp = _client.chat.completions.create(
            model=chat_model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
        )
        latency_s = time.perf_counter() - start_time
        return {
            "question":   question,
            "answer":     resp.choices[0].message.content,
            "sources":    [hit["chunk_id"] for hit in retrieved],
            "tokens_in":  resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
            "retrieved":  retrieved,  # full retrieved chunks for inspection
            "latency_s": latency_s
            }
    else:
        latency_s = time.perf_counter() - start_time
        return {
            "question":   question,
            "answer":     "",
            "sources":    [hit["chunk_id"] for hit in retrieved],
            "tokens_in":  0,
            "tokens_out": 0,
            "retrieved":  retrieved,  # full retrieved chunks for inspection
            "latency_s": latency_s
            }


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Cost in USD."""
    ##Use TikToken - currently defaulted
    cost = ((input_tokens*0.1) +(output_tokens*0.25) )/1_000_000
    return cost


def calculate_hit_rate(retrieved_chunk_ids: list[str], ground_truth_chunk_id: str) -> int:
    """
    Checks if the ground truth chunk is present in the top-K retrieved chunk IDs.
    Returns 1 (Hit) or 0 (Miss).
    """
    return 1 if ground_truth_chunk_id in retrieved_chunk_ids else 0



