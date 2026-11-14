"""Application settings, read from MF_* environment variables (and .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MF_", env_file=".env", extra="ignore")

    database_url: str
    secret_key: SecretStr
    data_dir: Path = Path("/data")
    bind_host: str = "127.0.0.1"
    bind_port: int = 8080
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    session_ttl_hours: int = 72
    # Peers whose X-Forwarded-For / X-Forwarded-Proto headers are trusted (IPs or CIDRs, or "*").
    trusted_proxies: list[str] = Field(default_factory=lambda: ["127.0.0.1"])

    @field_validator("secret_key")
    @classmethod
    def _secret_key_long_enough(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("MF_SECRET_KEY must be at least 32 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
