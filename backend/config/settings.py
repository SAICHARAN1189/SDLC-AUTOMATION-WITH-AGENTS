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

    groq_api_key: str = ""
    primary_model: str = "openai/gpt-oss-120b"
    fast_model: str = "openai/gpt-oss-20b"
    reasoning_model: str = "openai/gpt-oss-120b"
    comparison_models: str = "openai/gpt-oss-20b,openai/gpt-oss-120b"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "sdlc-artifacts"

    database_url: str = ""

    demo_mode: bool = True
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
