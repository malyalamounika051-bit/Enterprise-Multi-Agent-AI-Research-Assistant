import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Asterline AI Research Assistant"
    API_V1_PREFIX: str = "/api"
    
    # Storage & Database
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "asterline.db"
    CHROMA_PERSIST_DIR: Path = BASE_DIR / "data" / "chroma_db"
    CORPUS_PATH: Path = BASE_DIR / "data" / "corpus.jsonl"
    
    # Local Embedding Model
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # LLM Settings (Accessible hosted LLM or OpenAI-compatible endpoint)
    # Providers supported: gemini, openai, groq, ollama, mock
    LLM_PROVIDER: str = "gemini"  # or openai, groq, mock
    LLM_MODEL: str = "gemini-1.5-flash"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    GROQ_API_KEY: str = ""
    
    # LangSmith Observability
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "asterline-ai-assistant"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
