from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_env_file() -> Path:
    """Resolve the backend-local .env file regardless of the current working directory."""

    current = Path(__file__).resolve()
    for ancestor in current.parents:
        candidate = ancestor / ".env"
        if candidate.exists():
            return candidate
    return current.parents[3] / ".env"


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

    # Generation admission
    generation_max_concurrent_per_user: int = Field(default=2, ge=1)

    # Runtime concurrency
    pipeline_concurrency_draft_section_max: int = Field(default=6, ge=1)
    pipeline_concurrency_draft_diagram_max: int = Field(default=2, ge=1)
    pipeline_concurrency_draft_qc_max: int = Field(default=6, ge=1)

    pipeline_concurrency_balanced_section_max: int = Field(default=4, ge=1)
    pipeline_concurrency_balanced_diagram_max: int = Field(default=2, ge=1)
    pipeline_concurrency_balanced_qc_max: int = Field(default=4, ge=1)

    pipeline_concurrency_strict_section_max: int = Field(default=3, ge=1)
    pipeline_concurrency_strict_diagram_max: int = Field(default=1, ge=1)
    pipeline_concurrency_strict_qc_max: int = Field(default=3, ge=1)

    # Whole-generation timeout
    pipeline_timeout_generation_base_seconds: float = Field(default=120.0, gt=0)
    pipeline_timeout_generation_per_section_seconds: float = Field(default=90.0, gt=0)
    pipeline_timeout_generation_cap_seconds: float = Field(default=900.0, gt=0)

    # Node execution budgets
    pipeline_timeout_curriculum_seconds: float = Field(default=60.0, gt=0)
    pipeline_timeout_content_core_seconds: float = Field(default=180.0, gt=0)
    pipeline_timeout_content_practice_seconds: float = Field(default=120.0, gt=0)
    pipeline_timeout_content_enrichment_seconds: float = Field(default=90.0, gt=0)
    pipeline_timeout_content_repair_seconds: float = Field(default=120.0, gt=0)
    pipeline_timeout_field_regen_seconds: float = Field(default=60.0, gt=0)
    pipeline_timeout_qc_seconds: float = Field(default=60.0, gt=0)
    pipeline_timeout_diagram_inner_seconds: float = Field(default=45.0, gt=0)
    pipeline_timeout_diagram_node_budget_seconds: float = Field(default=60.0, gt=0)

    # Rerender budgets
    pipeline_rerender_draft_section_max: int = Field(default=1, ge=0)
    pipeline_rerender_balanced_section_max: int = Field(default=2, ge=0)
    pipeline_rerender_strict_section_max: int = Field(default=3, ge=0)

    # LLM retry attempts per node family
    pipeline_retry_curriculum_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_content_core_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_content_practice_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_content_enrichment_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_content_repair_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_field_regen_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_qc_max_attempts: int = Field(default=2, ge=1)
    pipeline_retry_diagram_max_attempts: int = Field(default=1, ge=1)

    # Output
    document_output_dir: str = "outputs/documents"
    report_output_dir: str = "outputs/reports"

    # Authentication
    google_client_id: str = ""
    jwt_secret_key: str = "CHANGE-ME"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "postgresql+asyncpg://textbook:textbook@localhost:5432/textbook_agent"
    run_migrations_on_startup: bool = True
    json_logging: bool = True

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Lesson Builder (share links point here)
    lesson_builder_public_url: str = "http://127.0.0.1:5173"


settings = Settings()
