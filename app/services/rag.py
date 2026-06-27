"""
Core RAG pipeline for NeuroBase.
Three-layer search: Qdrant (primary) → PubMed (academic) → Serply (web)
"""
import hashlib
import time
from typing import Optional
from app.services.vector_db import search as qdrant_search, upsert
from app.services.cache import cache_get, cache_set
from app.services.llm import embed_text, chat_completion
from app.core.config import get_settings

settings = get_settings()


# ─── Layer 1: Qdrant Vector Search ───────────────────────────────────────
async def search_qdrant(query: str, collection: str = "neurobase_flashcards", top_k: int = 5) -> list[dict]:
    try:
        vec = await embed_text(query)
        results = qdrant_search(collection, vec, top_k=top_k)
        return results
    except Exception as e:
        print(f"Qdrant search error: {e}")
        return []


# ─── Layer 2: PubMed (FREE, academic) ────────────────────────────────────
async def search_pubmed(query: str, top_k: int = 5) -> list[dict]:
    """Search PubMed via E-utilities (FREE, no API key)."""
    import httpx
    
    email = settings.PUBMED_EMAIL
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Search
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": top_k,
                "retmode": "json",
                "email": email,
                "sort": "relevance",
            }
            resp = await client.get(search_url, params=params)
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            
            if not ids:
                return []
            
            # Fetch details
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
                "email": email,
            }
            resp = await client.get(fetch_url, params=params)
            data = resp.json().get("result", {})
            
            for pub_id in ids:
                info = data.get(pub_id, {})
                results.append({
                    "source": "pubmed",
                    "id": pub_id,
                    "title": info.get("title", ""),
                    "authors": [a.get("name","") for a in info.get("authors", [])],
                    "journal": info.get("source", ""),
                    "year": info.get("pubdate", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pub_id}/",
                    "snippet": info.get("title", "")[:200],
                })
    except Exception as e:
        print(f"PubMed search error: {e}")
    
    return results


# ─── Layer 3: Serply Web Search ────────────────────────────────────────────
async def search_web(query: str, top_k: int = 3) -> list[dict]:
    """Web search via Serply (paid)."""
    if not settings.SERPLY_API_KEY:
        return []
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.serply.io/v1/search/",
                headers={
                    "Authorization": f"Bearer {settings.SERPLY_API_KEY}",
                    "Content-Type": "application/json",
                    "X-API-KEY": settings.SERPLY_API_KEY,
                },
                json={"q": query, "num": top_k},
            )
            items = resp.json().get("results", [])
            return [
                {
                    "source": "web",
                    "title": i.get("title", ""),
                    "url": i.get("link", ""),
                    "snippet": i.get("snippet", ""),
                }
                for i in items
            ]
    except Exception as e:
        print(f"Serply search error: {e}")
        return []


# ─── RAG Merge & Rerank ───────────────────────────────────────────────────
async def rag_query(
    user_query: str,
    user_id: str,
    collection: str = "neurobase_flashcards",
    use_pubmed: bool = True,
    use_web: bool = False,
) -> dict:
    """Full RAG pipeline: search → merge → generate."""
    
    # Check cache first (FAQ-style, keyed by hash of query)
    cache_key = f"faq:{hashlib.md5(user_query.lower().encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        return {"answer": cached, "sources": [], "cached": True}
    
    # Layer 1: Qdrant vector search
    docs = await search_qdrant(user_query, collection=collection)
    
    # Layer 2: PubMed (academic)
    pubmed_results = []
    if use_pubmed:
        pubmed_results = await search_pubmed(user_query)
    
    # Layer 3: Web (if enabled and no good Qdrant results)
    web_results = []
    if use_web and len(docs) < 2:
        web_results = await search_web(user_query)
    
    # Build context from Qdrant results
    context_parts = []
    citations = []
    
    for i, doc in enumerate(docs):
        payload = doc["payload"]
        # Support both flat and nested payload formats
        meta = payload.get("metadata", {})
        # Get the main content field (varies by content type)
        content = (payload.get("content") or payload.get("text") or 
                   payload.get("question", "") or payload.get("resposta", "") or "")
        
        context_parts.append(
            f"[{i+1}] {content}\n"
            f"Source: {meta.get('source', 'flashcard')}"
        )
        citations.append({
            "id": doc["id"],
            "score": doc["score"],
            "content": content[:200],
            "source": meta.get("source", "unknown"),
        })
    
    context = "\n\n".join(context_parts)
    
    # Build system prompt with context
    system_prompt = f"""You are the NeuroBase AI Tutor — an expert in neurosurgery and neurology education.

You have access to the following context from the user's study materials:
{context}

Instructions:
- Answer based ONLY on the provided context above
- If the context doesn't contain enough information, say "I don't have enough information in the study materials to answer this definitively. Based on general neurosurgical knowledge..." and provide a helpful answer
- Use Brazilian Portuguese for responses
- Format medical terms in English in *italics*
- Include citations like [1], [2] when referencing specific sources
- Be precise, clinical, and educational
- If showing a list or classification, use proper markdown tables
"""
    
    # Generate response
    answer = await chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        model=settings.OPENROUTER_LLM_MODEL,
        temperature=0.3,
        max_tokens=1024,
    )
    
    # Cache FAQ-style answers
    if len(docs) >= 2:  # Only cache if we had good results
        cache_set(cache_key, answer, ttl=3600)
    
    return {
        "answer": answer,
        "sources": citations,
        "pubmed": pubmed_results[:5],
        "web": web_results[:3],
        "cached": False,
    }
