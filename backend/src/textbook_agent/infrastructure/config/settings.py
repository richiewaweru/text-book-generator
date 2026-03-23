from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_env_file() -> Path:
    """Resolve the backend-local .env file regardless of the current working directory."""

    return Path(__file__).resolve().parents[4] / ".env"


def bootstrap_environment(env_file: str | Path | None = None) -> Path:
    """
    Load backend-local environment variables into ``os.environ`` once at startup.

    ``override=False`` preserves real process/CI variables while making local
    ``backend/.env`` values visible to code paths that read directly from
    ``os.getenv(...)`` such as the pipeline provider registry.
    """

    target = Path(env_file) if env_file is not None else _default_env_file()
    load_dotenv(target, override=False)
    return target


_ENV_FILE = bootstrap_environment()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    default_pagination_limit: int = 20

    # Output
    document_output_dir: str = "outputs/documents"
    report_output_dir: str = "outputs/reports"

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
