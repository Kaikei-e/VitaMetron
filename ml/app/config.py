from functools import lru_cache
from pathlib import Path

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings

SECRETS_DIR = Path("/run/secrets")


def _read_secret(name: str) -> str | None:
    """Read a Docker Secret file, returning None if unavailable."""
    path = SECRETS_DIR / name
    try:
        return path.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None


class Settings(BaseSettings):
    model_config = {"env_prefix": ""}

    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "vitametron"
    db_user: str = "vitametron"
    db_password: str = ""
    db_sslmode: str = "disable"
    model_store_path: str = "/app/model_store"
    log_level: str = "INFO"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gemma3:4b-it-qat"
    ollama_timeout: float = 120.0

    @model_validator(mode="after")
    def _load_secrets(self):
        if not self.db_password:
            secret = _read_secret("db_password")
            if secret:
                self.db_password = secret
        return self

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
