import secrets
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Provider
    provider: Literal["claude", "openai"] = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Models
    claude_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"

    # Pipeline behaviour
    max_retries: int = 2
    quality_check_enabled: bool = True
    temperature: float = 0.3

    # Output
    output_dir: str = "outputs/"
    output_format: Literal["html", "pdf"] = "html"

    # Authentication
    google_client_id: str = ""
    jwt_secret_key: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite+aiosqlite:///./textbook_agent.db"

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
