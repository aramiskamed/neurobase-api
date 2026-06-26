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
    return {
        "app_name": s.APP_NAME,
        "api_str": s.API_V1_STR,
        "qdrant_url": s.QDRANT_URL,
        "openrouter_key_set": bool(s.OPENROUTER_API_KEY),
    }

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "routes": [r.path for r in app.routes],
    }
