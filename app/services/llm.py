import httpx
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


async def embed_text(text: str, model: str = "openai/text-embedding-3-small") -> list[float]:
    """Generate embedding via OpenRouter."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": text[:8192],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def chat_completion(
    messages: list[dict],
    model: str = "anthropic/claude-sonnet-4",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Generate LLM response via OpenRouter."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
