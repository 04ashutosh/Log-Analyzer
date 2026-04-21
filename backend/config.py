from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Embedding model (downloaded once, cached locally)
    embedding_model: str = "all-MiniLM-L6-v2"

    # File ingestion limits
    max_file_size_mb: int = 50
    chunk_size_bytes: int = 4096

    # Clustering
    hdbscan_min_cluster_size: int = 2

    # Recommender
    rule_confidence_threshold: float = 0.5

    # CORS — Vite dev server + any local port
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# ← This line was missing
settings = Settings()
