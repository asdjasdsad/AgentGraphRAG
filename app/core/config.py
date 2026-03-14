from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
APP_ENV_PREFIX = "AGENTGRAPHRAG_"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix=APP_ENV_PREFIX,
        extra="ignore",
    )

    app_name: str = "AgentGraphRAG"
    app_env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api/v1"

    data_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    store_dir: Path = BASE_DIR / "data" / "store"

    llm_provider: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_api_version: str = ""

    embedding_provider: str = "local"
    embedding_model: str = "bge-m3"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_api_version: str = ""
    embedding_dimensions: int = 1024
    embedding_query_instruction: str = "为航空质量问题检索最相关的原因、措施、案例和证据"

    document_parse_provider: str = "local"
    document_parse_base_url: str = ""
    document_parse_api_key: str = ""

    mysql_url: str = "sqlite:///local.db"

    neo4j_mode: str = "local"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    milvus_mode: str = "local"
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_database: str = "default"
    milvus_collection: str = "chunks"

    default_top_k: int = 5
    max_chunk_chars: int = 500


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.store_dir.mkdir(parents=True, exist_ok=True)
    return settings


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
