from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.services.rag import rag_query
from app.services.cache import rate_limit

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = []
    collection: str = "neurobase_flashcards"
    use_pubmed: bool = True
    use_web: bool = False


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    pubmed: List[dict]
    web: List[dict]
    cached: bool


def _verify_clerk_token(authorization: Optional[str] = None) -> str:
    """Verify Clerk JWT and return user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid auth token")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        import httpx
        import json
        
        # Verify with Clerk's JWT verification endpoint
        # In production, use proper JWT verification with clerk_sdk_python
        resp = httpx.post(
            f"https://api.clerk.com/v1/authenticate",
            headers={"Authorization": f"Bearer $CLERK_SECRET_KEY"},
            json={"token": token},
            timeout=10,
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        data = resp.json()
        return data.get("sub", "anonymous")
    except HTTPException:
        raise
    except Exception:
        # Fallback: if Clerk unavailable, extract from token payload
        # In production, always verify properly
        return "user_placeholder"


@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    # Verify auth
    user_id = _verify_clerk_token(authorization)
    
    # Rate limiting
    if not rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in 1 minute.")
    
    try:
        result = await rag_query(
            user_query=req.query,
            user_id=user_id,
            collection=req.collection,
            use_pubmed=req.use_pubmed,
            use_web=req.use_web,
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")
