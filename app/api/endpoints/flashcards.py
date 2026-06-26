from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.services.vector_db import search as qdrant_search, upsert
from app.services.llm import embed_text
import uuid

router = APIRouter()


class FlashcardSearchResult(BaseModel):
    id: str
    content: str
    question: str
    answer: Optional[str]
    source: str
    score: float
    tags: List[str]


class FlashcardIngestRequest(BaseModel):
    cards: List[dict]  # [{content, answer, metadata}]
    collection: str = "neurobase_flashcards"


@router.get("/search", response_model=List[FlashcardSearchResult])
async def search_flashcards(
    q: str = Query(..., min_length=2),
    collection: str = "neurobase_flashcards",
    top_k: int = 10,
):
    try:
        vec = await embed_text(q)
        results = qdrant_search(collection, vec, top_k=top_k)
        
        output = []
        for r in results:
            payload = r.get("payload", {})
            # Support both flat payload (our format) and nested metadata
            inner = payload.get("metadata", payload)
            output.append(FlashcardSearchResult(
                id=str(r["id"]),
                content=payload.get("content", ""),
                question=payload.get("question", payload.get("content", "")[:100]),
                answer=payload.get("answer") or inner.get("answer", ""),
                source=inner.get("source", "unknown"),
                score=r.get("score", 0),
                tags=inner.get("tags", []),
            ))
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_flashcards(req: FlashcardIngestRequest):
    """Ingest flashcards into Qdrant."""
    try:
        from app.services.vector_db import ensure_collections
        ensure_collections()
        
        points = []
        for card in req.cards:
            content = f"Q: {card['content']}"
            if card.get("answer"):
                content += f"\nA: {card['answer']}"
            
            # Quick embed (sync for now)
            import asyncio
            vec = asyncio.get_event_loop().run_until_complete(embed_text(content))
            
            points.append({
                "id": card.get("id", str(uuid.uuid4())),
                "vector": vec,
                "content": content,
                "metadata": {
                    "type": "flashcard",
                    "source": card.get("source", "manual"),
                    "tags": card.get("tags", []),
                    "answer": card.get("answer", ""),
                },
            })
        
        upsert(req.collection, points)
        return {"inserted": len(points)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
