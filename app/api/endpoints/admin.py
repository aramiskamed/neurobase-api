from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class IngestRequest(BaseModel):
    collection: str = "neurobase_flashcards"
    force: bool = False

@router.post("/ingest")
async def trigger_ingestion(req: IngestRequest):
    """
    Trigger full ingestion pipeline.
    Set OPENROUTER_API_KEY and QDRANT_* vars via Railway dashboard.
    """
    try:
        from app.workers.ingestion import run_full_ingestion
        result = await run_full_ingestion()
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def admin_status():
    return {"service": "neurobase-api", "status": "ok", "version": "1.0.0"}
