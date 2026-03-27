from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_env_file() -> Path:
    """Resolve the backend-local .env file regardless of the current working directory."""

    return Path(__file__).resolve().parents[4] / ".env"


def _normalize_path_env(var_name: str, *, base_dir: Path) -> None:
    raw = os.getenv(var_name)
    if not raw:
        return

    candidate = Path(raw)
    if candidate.is_absolute():
        return

    os.environ[var_name] = str((base_dir / candidate).resolve())


def _normalize_sqlite_database_url(var_name: str, *, base_dir: Path) -> None:
    raw = os.getenv(var_name)
    if not raw or not raw.startswith("sqlite"):
        return

    _, separator, path_part = raw.partition(":///")
    if separator != ":///" or not path_part:
        return

    path = Path(path_part)
    if path.is_absolute():
        return

    resolved = (base_dir / path).resolve().as_posix()
    os.environ[var_name] = f"{raw[: raw.index(':///') + 4]}{resolved}"


def _normalize_backend_local_env_paths(env_file: Path) -> None:
    base_dir = env_file.parent
    _normalize_path_env("LECTIO_CONTRACTS_DIR", base_dir=base_dir)
    _normalize_sqlite_database_url("DATABASE_URL", base_dir=base_dir)


def bootstrap_environment(env_file: str | Path | None = None) -> Path:
    """
    Load backend-local environment variables into ``os.environ`` once at startup.

    ``override=False`` preserves real process/CI variables while making local
    ``backend/.env`` values visible to code paths that read directly from
    ``os.getenv(...)`` such as the pipeline provider registry.
    """

    target = Path(env_file) if env_file is not None else _default_env_file()
    load_dotenv(target, override=False)
    _normalize_backend_local_env_paths(target)
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
