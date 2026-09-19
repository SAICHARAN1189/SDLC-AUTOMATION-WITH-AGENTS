from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "gemini"
    enable_llm_fallback: bool = True

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fast_model: str = "gemini-3.8-flash"
    gemini_thinking_level: str = "low"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_fallback_model: str = "openai/gpt-oss-20b"

    primary_model: str = "gemini-3.8-flash"
    fast_model: str = "gemini-3.8-flash"
    reasoning_model: str = "gemini-3.8-flash"
    comparison_models: str = "gemini-3.8-flash,openai/gpt-oss-120b,openai/gpt-oss-20b,groq/compound,groq/compound-mini"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "sdlc-artifacts"

    database_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800
    db_connect_timeout: int = 10

    @property
    def normalized_database_url(self) -> str:
        url = (self.database_url or "").strip()
        if not url:
            return ""
        # SQLAlchemy 2.0 requires postgresql:// instead of postgres://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url

    demo_mode: bool = False
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    flask_env: str = "development"
    secret_key: str = "change-me-in-production"

    security_max_retries: int = 2
    qa_max_retries: int = 2
    review_max_retries: int = 2
    code_execution_timeout_seconds: int = 15

    @property
    def comparison_model_list(self) -> List[str]:
        return [item.strip() for item in self.comparison_models.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins

    @property
    def is_production(self) -> bool:
        return self.flask_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
