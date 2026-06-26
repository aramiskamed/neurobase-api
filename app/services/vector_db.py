import uuid
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import get_settings

settings = get_settings()


def get_client() -> QdrantClient:
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )


def ensure_collections():
    """Create collections if they don't exist."""
    client = get_client()
    
    collections = [
        (settings.QDRANT_COLLECTION_FLASH, 1536),
        (settings.QDRANT_COLLECTION_PROVAS, 1536),
        (settings.QDRANT_COLLECTION_LECTURES, 1536),
    ]
    
    for name, size in collections:
        existing = [c.name for c in client.get_collections().collections]
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
            print(f"Created collection: {name}")


def search(
    collection: str,
    query_vector: list[float],
    top_k: int = 5,
    user_id: Optional[str] = None,
    filters: Optional[dict] = None,
) -> list[dict]:
    """Search Qdrant collection."""
    client = get_client()
    
    query_filter = None
    if user_id:
        query_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
        )
    
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
        score_threshold=0.6,
    )
    
    return [
        {
            "id": r.id,
            "score": r.score,
            "payload": r.payload,
        }
        for r in results
    ]


def upsert(
    collection: str,
    points: list[dict],
    user_id: Optional[str] = None,
):
    """Upsert points to Qdrant."""
    client = get_client()
    
    structs = []
    for p in points:
        metadata = p.get("metadata", {})
        if user_id:
            metadata["user_id"] = user_id
        
        structs.append(PointStruct(
            id=str(p.get("id", uuid.uuid4())),
            vector=p["vector"],
            payload={
                "content": p["content"],
                "metadata": metadata,
            },
        ))
    
    client.upsert(
        collection_name=collection,
        points=structs,
    )
