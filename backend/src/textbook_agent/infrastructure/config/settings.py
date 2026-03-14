from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Provider
    provider: Literal["claude", "openai"] = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Models
    claude_model: str = "claude-sonnet-4-20250514"
    claude_fast_model: str = "claude-haiku-4-5-20251001"
    openai_model: str = "gpt-5-mini"
    openai_fast_model: str = "gpt-5-mini"
    llm_max_tokens: int = 4096

    # Pipeline behaviour
    max_retries: int = 2
    retry_base_delay: float = 1.0
    quality_check_enabled: bool = True
    max_quality_reruns: int = 3
    temperature: float = 0.3

    # Quality thresholds
    code_line_soft_limit: int = 80
    code_line_hard_limit: int = 300

    # API
    default_pagination_limit: int = 20

    # Output
    output_dir: str = "outputs/"
    output_format: Literal["html", "pdf"] = "html"

    # Authentication
    google_client_id: str = ""
    jwt_secret_key: str = "CHANGE-ME"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite+aiosqlite:///./textbook_agent.db"

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
