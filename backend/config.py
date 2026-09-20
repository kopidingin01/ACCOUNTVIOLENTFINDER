from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRETS = {
    "jwt_secret": "insecure-dev-secret-change-me",
    "encryption_secret": "insecure-dev-encryption-secret-change-me",
}

# Resolved relative to this file, not the current working directory, so
# `.env` at the repo root is found whether the app/scripts are launched
# from the repo root or from inside backend/ (e.g. `cd backend && python
# seed.py`) — a plain env_file=".env" only works in the former case and
# silently falls back to in-code defaults in the latter, which is exactly
# the kind of failure that should be loud, not silent.
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://report_validator:change_me@localhost:5432/report_validator"

    jwt_secret: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Independent from jwt_secret on purpose: this key encrypts secrets at
    # rest (platform API credentials, see services/crypto_service.py) while
    # jwt_secret signs auth tokens — a much more exposed value (sent to
    # every client indirectly via HS256-signed tokens, rotated during
    # incident response). Reusing one secret for both meant a JWT-secret
    # leak also decrypted every stored credential, and rotating it silently
    # broke existing ciphertext.
    encryption_secret: str = "insecure-dev-encryption-secret-change-me"

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

    @model_validator(mode="after")
    def _reject_insecure_default_secrets(self) -> "Settings":
        # These string defaults are public (they're in the repo on GitHub),
        # so starting with either one left unset would let anyone forge
        # auth tokens or decrypt stored platform credentials. Failing loudly
        # here beats silently running insecure — set JWT_SECRET and
        # ENCRYPTION_SECRET via the environment or .env before starting.
        leftover = [field for field, default in INSECURE_DEFAULT_SECRETS.items() if getattr(self, field) == default]
        if leftover:
            names = ", ".join(name.upper() for name in leftover)
            raise ValueError(
                f"{names} still set to its insecure built-in default. "
                "Set a real random value via the environment or .env before starting the app."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
