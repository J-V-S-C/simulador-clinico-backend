"""Validated runtime configuration. Secrets are never printed."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'clinical.db'}"
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    gemini_timeout_seconds: float = 15.0
    admin_username: str = ""
    admin_password: str = ""

    @property
    def api_key(self) -> str | None:
        return self.google_api_key or self.gemini_api_key

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]
