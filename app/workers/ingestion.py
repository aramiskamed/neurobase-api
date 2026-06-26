"""
Batch ingestion worker for NeuroBase.
Processes flashcard JSON files → generates embeddings → upserts to Qdrant.
"""
import json
import os
import asyncio
from pathlib import Path
from app.workers.parser import parse_deck1_flashcard, parse_sbn_question, parse_kt_mcq
from app.services.llm import embed_text
from app.services.vector_db import upsert, ensure_collections
from app.core.config import get_settings

settings = get_settings()


async def ingest_deck1_files(files: list[str], collection: str) -> dict:
    """Ingest all Deck1 flashcard JSON files."""
    total = 0
    errors = 0
    
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cards = json.load(f)
            
            if not isinstance(cards, list):
                cards = [cards]
            
            points = []
            for card in cards:
                parsed = parse_deck1_flashcard(card)
                if not parsed:
                    errors += 1
                    continue
                
                try:
                    vec = await embed_text(parsed["content"])
                    points.append({
                        "id": parsed["id"],
                        "vector": vec,
                        "content": parsed["content"],
                        "metadata": parsed["metadata"],
                    })
                    total += 1
                    
                    # Batch every 50 cards
                    if len(points) >= 50:
                        upsert(collection, points)
                        points = []
                        print(f"  [{filepath}] Ingested {total} cards so far...")
                        
                except Exception as e:
                    print(f"  Embedding error for {parsed['id']}: {e}")
                    errors += 1
            
            # Flush remaining
            if points:
                upsert(collection, points)
                
            print(f"✅ {filepath}: {len(cards)} cards processed")
            
        except Exception as e:
            print(f"❌ File error {filepath}: {e}")
    
    return {"total": total, "errors": errors}


async def ingest_sbn_questions(files: list[str], collection: str) -> dict:
    """Ingest SBN/R1-R5 exam questions."""
    total = 0
    errors = 0
    
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                questions = json.load(f)
            
            if not isinstance(questions, list):
                questions = [questions]
            
            points = []
            for entry in questions:
                parsed = parse_sbn_question(entry)
                if not parsed:
                    errors += 1
                    continue
                
                try:
                    vec = await embed_text(parsed["content"])
                    points.append({
                        "id": parsed["id"],
                        "vector": vec,
                        "content": parsed["content"],
                        "metadata": parsed["metadata"],
                    })
                    total += 1
                    
                    if len(points) >= 50:
                        upsert(collection, points)
                        points = []
                        
                except Exception as e:
                    errors += 1
            
            if points:
                upsert(collection, points)
            
            print(f"✅ {filepath}: {total} questions processed")
            
        except Exception as e:
            print(f"❌ File error {filepath}: {e}")
    
    return {"total": total, "errors": errors}


async def ingest_kt_mcq(files: list[str], collection: str) -> dict:
    """Ingest Knowledge Testing MCQs."""
    total = 0
    errors = 0
    
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                questions = json.load(f)
            
            if not isinstance(questions, list):
                questions = [questions]
            
            points = []
            for entry in questions:
                parsed = parse_kt_mcq(entry)
                if not parsed:
                    errors += 1
                    continue
                
                try:
                    vec = await embed_text(parsed["content"])
                    points.append({
                        "id": parsed["id"],
                        "vector": vec,
                        "content": parsed["content"],
                        "metadata": parsed["metadata"],
                    })
                    total += 1
                    
                    if len(points) >= 50:
                        upsert(collection, points)
                        points = []
                        
                except Exception as e:
                    errors += 1
            
            if points:
                upsert(collection, points)
            
            print(f"✅ {filepath}: {total} MCQs processed")
            
        except Exception as e:
            print(f"❌ File error {filepath}: {e}")
    
    return {"total": total, "errors": errors}


async def run_full_ingestion():
    """Run the complete ingestion pipeline."""
    print("🚀 Starting NeuroBase ingestion pipeline...")
    
    # Ensure collections exist
    ensure_collections()
    
    # ─── Deck1 Flashcards ───────────────────────────────────────────
    deck1_files = [
        "/workspace/deck1_new_cards_2a_radiologia.json",
        "/workspace/deck1_new_cards_2b_dbs.json",
        "/workspace/deck1_new_cards_2c_neuroftalmologia.json",
        "/workspace/deck1_new_cards_3a_neuroftalmo.json",
        "/workspace/deck1_new_cards_avc_neurocritical.json",
    ]
    existing_deck1 = [f for f in deck1_files if os.path.exists(f)]
    print(f"\n📚 Deck1 flashcards: {len(existing_deck1)} files")
    deck1_result = await ingest_deck1_files(existing_deck1, settings.QDRANT_COLLECTION_FLASH)
    
    # ─── SBN/R1-R5 Questions ──────────────────────────────────────────
    sbn_files = [
        "/workspace/neurobase/parsed/R1_2022.json",
        "/workspace/neurobase/parsed/R1_2024_topics.json",
        "/workspace/neurobase/parsed/R2_2024_topics.json",
        "/workspace/neurobase/parsed/R3_2024_topics.json",
        "/workspace/neurobase/parsed/R3_2024_content.json",
        "/workspace/neurobase/parsed/R4_2024_topics.json",
        "/workspace/neurobase/parsed/R5_2024_topics.json",
    ]
    existing_sbn = [f for f in sbn_files if os.path.exists(f)]
    print(f"\n📝 SBN Questions: {len(existing_sbn)} files")
    sbn_result = await ingest_sbn_questions(existing_sbn, settings.QDRANT_COLLECTION_PROVAS)
    
    # ─── Knowledge Testing MCQs ───────────────────────────────────────
    kt_files = [
        "/workspace/pacote_neurocirurgia_boards/output/05_meta/kt_parsed.json",
        "/workspace/pacote_neurocirurgia_boards/output/05_meta/kt_all_parsed.json",
        "/workspace/pacote_neurocirurgia_boards/output/05_meta/sampled_questions.json",
    ]
    existing_kt = [f for f in kt_files if os.path.exists(f)]
    print(f"\n📖 Knowledge Testing: {len(existing_kt)} files")
    kt_result = await ingest_kt_mcq(existing_kt, settings.QDRANT_COLLECTION_PROVAS)
    
    # ─── Summary ─────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"📊 Ingestion Summary:")
    print(f"  Flashcards: {deck1_result['total']} | errors: {deck1_result['errors']}")
    print(f"  SBN Questions: {sbn_result['total']} | errors: {sbn_result['errors']}")
    print(f"  KT MCQs: {kt_result['total']} | errors: {kt_result['errors']}")
    print(f"{'='*50}")
    
    return {
        "flashcards": deck1_result,
        "sbn": sbn_result,
        "kt": kt_result,
    }
