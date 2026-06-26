#!/usr/bin/env python3
"""
NeuroBase Ingestion CLI
Usage:
  python -m app.workers.ingest_cli --dry-run    # Preview without uploading
  python -m app.workers.ingest_cli --run        # Full ingestion

Environment variables required:
  OPENROUTER_API_KEY - your OpenRouter API key
  QDRANT_URL - Qdrant cluster URL
  QDRANT_API_KEY - Qdrant API key
"""
import argparse
import asyncio


async def main():
    parser = argparse.ArgumentParser(description="NeuroBase Ingestion Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview cards without ingesting")
    parser.add_argument("--run", action="store_true", help="Run full ingestion")
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE — Previewing data...")
        from app.workers.parser import parse_deck1_flashcard
        import json
        
        with open("/workspace/deck1_new_cards_2a_radiologia.json") as f:
            cards = json.load(f)
        
        for i, card in enumerate(cards[:5]):
            parsed = parse_deck1_flashcard(card)
            if parsed:
                print(f"\n--- Card {i+1} ---")
                print(f"Q: {parsed['question'][:100]}...")
                print(f"Tags: {parsed['metadata']['tags']}")
        return
    
    if args.run:
        print("RUNNING INGESTION...")
        from app.workers.ingestion import run_full_ingestion
        result = await run_full_ingestion()
        print(f"\nDone! Result: {result}")
        return
    
    print("Use --dry-run or --run")


if __name__ == "__main__":
    asyncio.run(main())
