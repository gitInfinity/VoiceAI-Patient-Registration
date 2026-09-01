from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Voice AI Patient Registration API"
    database_url: str = "sqlite:///./voice_agent.db"
    log_level: str = "INFO"
    vapi_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("VAPI_API_KEY", "PRIVATE_VAPI_KEY"),
    )
    vapi_assistant_id: str | None = None
    vapi_tool_secret: SecretStr | None = None
    vapi_credential_id: str | None = None
    public_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Select psycopg 3 for Railway-style PostgreSQL URLs."""
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
