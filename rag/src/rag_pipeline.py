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
import re


# Qdrant DB
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

assert os.environ.get("QDRANT_URL"),     "Set QDRANT_URL — get free-tier at cloud.qdrant.io"
assert os.environ.get("QDRANT_API_KEY"), "Set QDRANT_API_KEY — from your Qdrant Cloud cluster"


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


def calc_golden_hit_cost_lat(responses: list) -> dict:
    Total = 0
    Hit_rate = 0
    Latency = 0
    total_cost_usd = 0
    for result in responses:
        Total = Total + 1
        Hit_rate = Hit_rate + result['hit_rate']
        Latency = Latency + result['latency_s']
        total_cost_usd = total_cost_usd + result['cost']
    return {"total_hits":Total, "hit_rate": Hit_rate, "latency": Latency, "total_cost_usd": total_cost_usd}



qdrant = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

# Sanity check — list existing collections
existing = qdrant.get_collections()
print(f"Connected to Qdrant at {os.environ['QDRANT_URL'][:40]}...")
#print(f"Existing collections: {[c.name for c in existing.collections]}")
#print("\n[] (empty), — this is a fresh cluster.")



COLLECTION_NAME = "sample_collection"

#Create collection

def create_collection(coll_name: str =COLLECTION_NAME):
    # Delete any prior version — makes this cell re-runnable
    try:
        qdrant.delete_collection(coll_name)
        print(f"Deleted existing {coll_name!r} collection.")
    except Exception:
        pass  # didn't exist yet

    # Create fresh
    qdrant.create_collection(
        collection_name=coll_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    info = qdrant.get_collection(coll_name)
    print(f"Created collection {coll_name!r}")
    print(f"  dim:      {info.config.params.vectors.size}")
    print(f"  metric:   {info.config.params.vectors.distance}")
    print(f"  points:   {info.points_count}")


# Upsert - Insert/ update the data into collections

def upsert_collection(coll_name: str, index_docs: list[dict] | str):
    import ast
    
    if coll_name =="":
        coll_name = COLLECTION_NAME
    print(index_docs)

    #if isinstance(index_doc, str):
    #    index_doc = ast.literal_eval(index_doc)

    points = [
        PointStruct(
            id=idx,
            vector=doc["vector"],
            payload={
                "source_id": doc["source_id"],
                "chunk_id":  doc["chunk_id"],
                "text":      doc["text"],
            },
        )
        for idx, doc in enumerate(index_docs)
    ]

    qdrant.upsert(collection_name=coll_name, points=points)

    # Verify
    info = qdrant.get_collection(coll_name)
    print(f"Upserted {len(points)} points.")
    print(f"Collection now has {info.points_count} points.")


async def retrive_from_collection(q_vec: list, coll_name: str=COLLECTION_NAME, k: int =3 ):
    if len(q_vec) > 0 and isinstance(q_vec[0], list):
        q_vec = q_vec[0]

    results = qdrant.query_points(
        collection_name=coll_name,
        query=q_vec,
        limit=k,
    ).points
    return results

async def dense_search(query: str, COLLECTION_NAME: str, k: int=3):
    qry = []
    qry.append(query)
    q_vec = embed_batch(qry)
    top5_vec = await retrive_from_collection(q_vec, COLLECTION_NAME, 5)
    dense_results = [
        {
            "chunk_id": pt.payload.get("chunk_id"),
            "source_id": pt.payload.get("source_id"),
            "text": pt.payload.get("text"),
            "score": pt.score,
        }
        for pt in top5_vec
    ]
    return dense_results

def delete_collection(coll_name: str=COLLECTION_NAME):
    try:
        qdrant.delete_collection(COLLECTION)
        return "Deletion success"
    except Exception:
        return Exception


def fetch_all_chunks_from_qdrant(coll_name: str) -> list[dict]:
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY"),
    )
    
    all_chunks = []
    next_offset = None

    while True:
        # Batch retrieve records without downloading vectors
        records, next_offset = client.scroll(
            collection_name=coll_name,
            limit=250,           # Number of points per network request
            with_payload=True,   # Includes text, sourceid, etc.
            with_vectors=False,  # Speeds up fetch time
            offset=next_offset
        )
        
        for point in records:
            payload = point.payload or {}
            all_chunks.append({
                # Prefers payload['chunkid'] if present, otherwise falls back to Qdrant's point.id
                "chunk_id": payload.get("chunk_id", point.id),
                "source_id": payload.get("source_id", ""),
                "text": payload.get("text", "")
            })
            
        # None means all points have been retrieved
        if next_offset is None:
            break
            
    return all_chunks



def simple_tokenize(text: str) -> list[str]:
    """Lowercase + word-and-alphanumeric-token split.
    """
    text = text.lower()
    # Match tokens: sequences of word chars possibly containing hyphens/slashes
    # This keeps 'ac-1042' and '/v2/dashboards' as single tokens
    return re.findall(r'[a-z0-9][a-z0-9\-/_]*', text)


def build_bm25_index(corpus: list[dict]):
    """Build a rank-bm25 BM25Okapi index over the corpus text field."""
    from rank_bm25 import BM25Okapi
    tokenized_corpus = [simple_tokenize(doc["text"] + " " + doc["source_id"]) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


async def bm25_search(query: str, index, corpus: list[dict],  k: int = 3) -> list[dict]:
    """Query BM25 index; return top-K docs with scores."""
    tokens = simple_tokenize(query)
    scores = index.get_scores(tokens)
    ranked = sorted(zip(scores, corpus), key=lambda pair: pair[0], reverse=True)
    retrived = [
        {"chunk_id": doc["chunk_id"], "source_id": doc["source_id"], "score": float(score), "text": doc["text"]}
        for score, doc in ranked[:k]
    ]
    return retrived



def rrf_fuse(ranked_lists: list[list[dict]], k: int = 60, top_n: int = 10) -> list[dict]:
    """Fuse multiple ranked result lists via Reciprocal Rank Fusion.
    RRF formula:  score(doc) = sum_over_lists( 1 / (k + rank_in_list) )
    k=60 is the Cormack et al. (2009) default — high enough to make top-1
    only slightly more valuable than top-2 (prevents any single retriever
    from dominating), low enough that rank still matters.
    Each ranked_list contains dicts with 'id' key. Returns fused ranking.
    """
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for ranked in ranked_lists:
        #print(f"Ranked: {ranked}")
        for rank, hit in enumerate(ranked, start=1): 
         #   print(f"rank: {rank} <<>> hit: {hit}")
            doc_id = hit["chunk_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in docs:
                docs[doc_id] = hit
    
    fused = sorted(scores.items(), key=lambda p: p[1], reverse=True)[:top_n]
    return [
        {**docs[doc_id], "rrf_score": score}
        for doc_id, score in fused
    ]



async def process_goldenset_dense_search(qry, qry_vec, coll_name, k):    
    topK_vec = await retrive_from_collection(qry_vec, coll_name, k)
    # Parse
    parsed_results = [
        {
            "chunk_id": pt.payload.get("chunk_id"),
            "source_id": pt.payload.get("source_id"),
            "text": pt.payload.get("text"),
            "score": pt.score,
        }
        for pt in topK_vec
    ]
    # Generate RAG response

##    return await ask_rag(qry_vec, parsed_results, k)
    return {"question": qry, 
            "retrived": parsed_results
    }