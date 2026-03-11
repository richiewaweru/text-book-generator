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


settings = Settings()
