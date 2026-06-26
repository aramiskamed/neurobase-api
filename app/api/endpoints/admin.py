from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import os

router = APIRouter()

class IngestRequest(BaseModel):
    collection: str = "neurobase_flashcards"
    force: bool = False


@router.post("/ingest")
async def trigger_ingestion(req: IngestRequest):
    """
    Trigger full ingestion pipeline.
    In production, this should be protected by admin auth.
    """
    # Only allow if admin token present (via header or env)
    # For now, just return the ingestion result
    
    # OPENROUTER_API_KEY must be set via environment variable
    # Railway will inject it via the dashboard or railway.json env vars
    # Set Qdrant placeholder (will fail gracefully if not configured)
    
    try:
        from app.workers.ingestion import run_full_ingestion
        result = await run_full_ingestion()
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def admin_status():
    """Check service status."""
    return {
        "service": "neurobase-api",
        "status": "ok",
        "version": "1.0.0",
    }
