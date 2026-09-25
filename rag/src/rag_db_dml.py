import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import asyncio


assert os.environ.get("QDRANT_URL"),     "Set QDRANT_URL — get free-tier at cloud.qdrant.io"
assert os.environ.get("QDRANT_API_KEY"), "Set QDRANT_API_KEY — from your Qdrant Cloud cluster"


qdrant = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

# Sanity check — list existing collections
existing = qdrant.get_collections()
print(f"Connected to Qdrant at {os.environ['QDRANT_URL'][:40]}...")
print(f"Existing collections: {[c.name for c in existing.collections]}")
print("\n[] (empty), — this is a fresh cluster.")



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

def delete_collection(coll_name: str=COLLECTION_NAME):
    try:
        qdrant.delete_collection(COLLECTION)
        return "Deletion success"
    except Exception:
        return Exception