"""
Application settings — 12-factor style configuration.

Industry practice: never hardcode secrets. Load from environment /
.env via pydantic-settings. Typed settings catch misconfiguration at
startup instead of at 2 AM in production.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object injected across the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- App -----
    app_name: str = "InterviewAI Pro"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(
        default="dev-only-insecure-secret-key-change-in-production-please-64chars",
        min_length=32,
    )
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    email_verification_expire_hours: int = 24
    password_reset_expire_hours: int = 1
    jwt_algorithm: str = "HS256"

    # ----- CORS -----
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # ----- Database -----
    postgres_user: str = "interviewai"
    postgres_password: str = "interviewai_dev_password"
    postgres_db: str = "interviewai"
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    database_url: str | None = None

    # ----- Redis / Celery -----
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: str | None = None
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # ----- Storage -----
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./storage/local"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_s3_region: str = "us-east-1"
    aws_s3_endpoint_url: str = ""  # MinIO / R2 optional
    resume_max_upload_mb: int = 5
    resume_allowed_content_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/msword,"
        "text/plain"
    )
    audio_max_upload_mb: int = 10
    audio_allowed_content_types: str = (
        "audio/webm,audio/wav,audio/wave,audio/x-wav,audio/mpeg,audio/mp4,audio/ogg,video/webm"
    )
    openai_whisper_model: str = "whisper-1"

    # ----- AI (used from Module 5+) -----
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ai_primary_provider: Literal["openai", "gemini"] = "openai"
    ats_use_llm_suggestions: bool = True


    # ----- Frontend / email -----
    frontend_url: str = "http://localhost:5173"
    email_from: str = "noreply@interviewaipro.local"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # ----- OAuth -----
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # ----- Bootstrap admin (Module 4 seed) -----
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "AdminPass1"
    seed_admin_name: str = "Platform Admin"

    # ----- Demo account (Module 14) -----
    seed_demo_enabled: bool = True
    seed_demo_email: str = "demo@interviewai.local"
    seed_demo_password: str = "DemoPass1"
    seed_demo_name: str = "Demo Candidate"

    # ----- Billing (Module 15) -----
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""
    billing_force_local: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_connection_url(self) -> str:
        return self.redis_url or f"redis://{self.redis_host}:{self.redis_port}/0"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or f"redis://{self.redis_host}:{self.redis_port}/1"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or f"redis://{self.redis_host}:{self.redis_port}/2"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resume_allowed_types_list(self) -> list[str]:
        return [t.strip() for t in self.resume_allowed_content_types.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings singleton.

    lru_cache ensures we parse env vars once per process.
    In tests, call get_settings.cache_clear() before overriding env.
    """
    return Settings()
