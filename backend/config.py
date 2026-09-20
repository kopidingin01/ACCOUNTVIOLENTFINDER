from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://report_validator:change_me@localhost:5432/report_validator"

    jwt_secret: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    search_provider: str = "none"
    search_api_key: str = ""

    platform_api_key: str = ""

    storage_path: str = "./storage/evidence"
    max_upload_mb: int = 25

    cors_origins: str = "http://localhost:5173"

    evidence_retention_days: int = 365
    case_retention_days: int = 730
    audit_retention_days: int = 1825

    rate_limit_per_minute: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
