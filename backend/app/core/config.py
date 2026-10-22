"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the semantic change detection backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Semantic Change Detection"
    app_version: str = "1.0.0"

    embedding_model: str = "all-MiniLM-L6-v2"
    nli_model: str = "cross-encoder/nli-deberta-v3-base"
    enable_nli: bool = True
    ner_model: str = "en_core_web_sm"

    similarity_threshold: float = 0.65
    paraphrase_threshold: float = 0.82
    unchanged_similarity_threshold: float = 0.90
    cross_section_similarity_threshold: float = 0.80
    nli_contradiction_threshold: float = 0.70
    nli_entailment_threshold: float = 0.70
    embedding_batch_size: int = 32
    nli_batch_size: int = 16
    alignment_hungarian_limit: int = 250

    database_url: str = "sqlite:///./data/semantic_changes.db"
    max_upload_size_mb: int = 50
    upload_dir: str = "./data/uploads"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
