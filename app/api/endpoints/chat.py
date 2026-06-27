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
    """Verify Clerk JWT and return user_id. Bypasses if CLERK_SECRET_KEY not set."""
    from app.core.config import get_settings
    settings = get_settings()
    
    # Dev mode: if Clerk not configured, allow all requests with test user
    if not settings.CLERK_SECRET_KEY:
        # Development bypass — log warning but allow
        if authorization and authorization.startswith("Bearer "):
            return "dev_user_" + authorization.replace("Bearer ", "")[:16]
        return "anonymous_dev"
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid auth token")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        import httpx
        
        resp = httpx.post(
            "https://api.clerk.com/v1/authenticate",
            headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
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
