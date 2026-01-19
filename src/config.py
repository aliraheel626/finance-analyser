"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_path: Path = Path("budget_tracker.db")

    # OpenAI API for TransactionAnnotationService
    openai_api_key: Optional[str] = None

    # Pagination
    default_page_size: int = 20

    @property
    def database_url(self) -> str:
        """Get SQLite connection URL."""
        return f"sqlite:///{self.database_path}"


settings = Settings()
