from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.api.endpoints import flashcards, chat, auth, content, admin

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.APP_NAME}...")
    yield
    print("Shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(flashcards.router, prefix=f"{settings.API_V1_STR}/flashcards", tags=["flashcards"])
app.include_router(content.router, prefix=f"{settings.API_V1_STR}/content", tags=["content"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/debug")
def debug():
    from app.core.config import get_settings
    s = get_settings()
    
    # Test Qdrant connection
    qdrant_ok = False
    qdrant_collections = []
    qdrant_error = ""
    
    try:
        from qdrant_client import QdrantClient
        c = QdrantClient(url=s.QDRANT_URL, api_key=s.QDRANT_API_KEY if s.QDRANT_API_KEY else None)
        cols = c.get_collections()
        qdrant_collections = [x.name for x in cols.collections]
        qdrant_ok = True
    except Exception as e:
        qdrant_error = str(e)
    
    return {
        "app_name": s.APP_NAME,
        "env_vars": {
            "QDRANT_URL_set": bool(s.QDRANT_URL),
            "QDRANT_URL_value": s.QDRANT_URL,
            "QDRANT_API_KEY_set": bool(s.QDRANT_API_KEY),
            "OPENROUTER_API_KEY_set": bool(s.OPENROUTER_API_KEY),
            "MINIMAX_API_KEY_set": bool(s.MINIMAX_API_KEY),
            "CLERK_SECRET_KEY_set": bool(s.CLERK_SECRET_KEY),
        },
        "qdrant": {
            "connected": qdrant_ok,
            "error": qdrant_error,
            "collections": qdrant_collections,
        },
    }

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "routes": [r.path for r in app.routes],
    }
