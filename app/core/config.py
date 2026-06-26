from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NeuroBase API"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Railway env vars (set via Railway dashboard)
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    
    # Qdrant
    QDRANT_URL: str = "https://8f34dea3.us-west-2.cloud.qdrant.io"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_FLASH: str = "neurobase_flashcards"
    QDRANT_COLLECTION_PROVAS: str = "neurobase_provas"
    QDRANT_COLLECTION_LECTURES: str = "neurobase_lectures"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    
    # Upstash Redis
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    
    # OpenRouter (embeddings + LLM routing)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    OPENROUTER_LLM_MODEL: str = "anthropic/claude-sonnet-4"
    
    # MiniMax (TTS + main LLM)
    MINIMAX_API_KEY: str = ""
    MINIMAX_BASE_URL: str = "https://api.minimax.chat/v1"
    
    # PubMed
    PUBMED_EMAIL: str = "neurobase@example.com"
    
    # Content limits
    MAX_TOKENS_EMBED: int = 8192
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
