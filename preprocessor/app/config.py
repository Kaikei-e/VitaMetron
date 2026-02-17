from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
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
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    upload_dir: str = "/data/uploads"
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _load_secrets(self):
        if not self.db_password:
            secret = _read_secret("db_password")
            if secret:
                self.db_password = secret
        if not self.redis_password:
            secret = _read_secret("redis_password")
            if secret:
                self.redis_password = secret
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
