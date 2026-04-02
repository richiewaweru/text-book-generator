from __future__ import annotations

import os
from pathlib import Path
import tomllib

import pytest
from pydantic import ValidationError

from core.config import Settings, bootstrap_environment
from core.database.session import build_engine_kwargs
from pipeline.runtime_policy import resolve_generation_timeout_seconds, resolve_runtime_policy_bundle
from pipeline.types.requests import GenerationMode


def _snapshot_env(*names: str) -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in names}


def _restore_env(snapshot: dict[str, str | None]) -> None:
    for name, value in snapshot.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_bootstrap_environment_loads_missing_values_without_overwriting_existing(
    monkeypatch,
    tmp_path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ANTHROPIC_API_KEY=file-anthropic-key",
                "PIPELINE_FAST_PROVIDER=openai_compatible",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("PIPELINE_FAST_PROVIDER", "anthropic")

    snapshot = _snapshot_env("ANTHROPIC_API_KEY", "PIPELINE_FAST_PROVIDER")
    try:
        loaded = bootstrap_environment(env_file)

        assert loaded == env_file
        assert os.getenv("ANTHROPIC_API_KEY") == "file-anthropic-key"
        assert os.getenv("PIPELINE_FAST_PROVIDER") == "anthropic"
    finally:
        _restore_env(snapshot)


def test_bootstrap_environment_resolves_relative_backend_local_paths(
    monkeypatch,
    tmp_path,
) -> None:
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LECTIO_CONTRACTS_DIR=./contracts",
                "DATABASE_URL=sqlite+aiosqlite:///./textbook_agent.db",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("LECTIO_CONTRACTS_DIR", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    snapshot = _snapshot_env("LECTIO_CONTRACTS_DIR", "DATABASE_URL")
    try:
        bootstrap_environment(env_file)

        assert os.getenv("LECTIO_CONTRACTS_DIR") == str(contracts_dir.resolve())
        assert os.getenv("DATABASE_URL") == f"sqlite+aiosqlite:///{(tmp_path / 'textbook_agent.db').resolve().as_posix()}"
    finally:
        _restore_env(snapshot)


def test_bootstrap_environment_preserves_absolute_sqlite_overrides(
    monkeypatch,
    tmp_path,
) -> None:
    db_path = (tmp_path / "absolute.db").resolve()
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL=sqlite+aiosqlite:///{db_path.as_posix()}\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)

    snapshot = _snapshot_env("DATABASE_URL")
    try:
        bootstrap_environment(env_file)

        assert os.getenv("DATABASE_URL") == f"sqlite+aiosqlite:///{db_path.as_posix()}"
    finally:
        _restore_env(snapshot)


def test_bootstrap_environment_preserves_postgres_urls(
    monkeypatch,
    tmp_path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://textbook:textbook@localhost:5432/textbook_agent\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("DATABASE_URL", raising=False)

    snapshot = _snapshot_env("DATABASE_URL")
    try:
        bootstrap_environment(env_file)

        assert (
            os.getenv("DATABASE_URL")
            == "postgresql+asyncpg://textbook:textbook@localhost:5432/textbook_agent"
        )
    finally:
        _restore_env(snapshot)


def test_runtime_policy_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    bundle = resolve_runtime_policy_bundle(settings, GenerationMode.BALANCED)

    assert settings.generation_max_concurrent_per_user == 2
    assert bundle.concurrency.max_section_concurrency == 4
    assert bundle.concurrency.max_diagram_concurrency == 2
    assert bundle.concurrency.max_qc_concurrency == 4
    assert bundle.max_section_rerenders == 2
    assert bundle.retries.qc_agent.max_attempts == 2
    assert resolve_generation_timeout_seconds(settings, 3) == 390.0
    assert resolve_generation_timeout_seconds(settings, 20) == 900.0


def test_runtime_policy_settings_read_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GENERATION_MAX_CONCURRENT_PER_USER", "5")
    monkeypatch.setenv("PIPELINE_CONCURRENCY_STRICT_DIAGRAM_MAX", "2")
    monkeypatch.setenv("PIPELINE_TIMEOUT_GENERATION_BASE_SECONDS", "150")
    monkeypatch.setenv("PIPELINE_TIMEOUT_GENERATION_PER_SECTION_SECONDS", "75")
    monkeypatch.setenv("PIPELINE_TIMEOUT_GENERATION_CAP_SECONDS", "600")
    monkeypatch.setenv("PIPELINE_RETRY_QC_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("PIPELINE_RERENDER_STRICT_SECTION_MAX", "6")

    settings = Settings(_env_file=None)
    bundle = resolve_runtime_policy_bundle(settings, GenerationMode.STRICT)

    assert settings.generation_max_concurrent_per_user == 5
    assert bundle.concurrency.max_diagram_concurrency == 2
    assert bundle.max_section_rerenders == 6
    assert bundle.retries.qc_agent.max_attempts == 4
    assert resolve_generation_timeout_seconds(settings, 4, mode=GenerationMode.STRICT) == 450.0


def test_runtime_policy_settings_reject_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_TIMEOUT_QC_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_engine_kwargs_use_db_echo_for_sqlite() -> None:
    kwargs = build_engine_kwargs("sqlite+aiosqlite:///./test.db", db_echo=True)

    assert kwargs == {"echo": True}


def test_engine_kwargs_add_postgres_pool_settings() -> None:
    kwargs = build_engine_kwargs(
        "postgresql+asyncpg://textbook:textbook@localhost:5432/textbook_agent",
        db_echo=False,
    )

    assert kwargs == {
        "echo": False,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


def test_settings_allow_local_defaults_in_development(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-development-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "http://127.0.0.1:5173")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./textbook_agent.db")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.db_echo is False


def test_settings_reject_placeholder_secret_in_development(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./textbook_agent.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-to-a-random-secret")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "http://127.0.0.1:5173")

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_settings_reject_placeholder_secret_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://textbook:textbook@db:5432/textbook_agent")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-to-a-random-secret")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "https://app.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "example-google-client-id")

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_settings_reject_local_origins_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://textbook:textbook@db:5432/textbook_agent")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-production-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:3000")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "https://app.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "example-google-client-id")

    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN"):
        Settings(_env_file=None)


def test_settings_require_google_client_id_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://textbook:textbook@db:5432/textbook_agent")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-production-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "https://app.example.com")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    with pytest.raises(ValidationError, match="GOOGLE_CLIENT_ID"):
        Settings(_env_file=None)


def test_settings_accept_safe_production_configuration(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://textbook:textbook@db:5432/textbook_agent")
    monkeypatch.setenv("DB_ECHO", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-production-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "https://app.example.com")
    monkeypatch.setenv("PDF_RENDER_BASE_URL", "https://app.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "example-google-client-id")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.db_echo is True


def test_settings_accept_json_logs_env_aliases(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./textbook_agent.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-development-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "http://127.0.0.1:5173")
    monkeypatch.setenv("JSON_LOGGING", "true")
    monkeypatch.delenv("JSON_LOGS", raising=False)

    legacy_settings = Settings(_env_file=None)

    monkeypatch.setenv("JSON_LOGS", "true")
    monkeypatch.delenv("JSON_LOGGING", raising=False)
    canonical_settings = Settings(_env_file=None)

    assert legacy_settings.json_logs is True
    assert canonical_settings.json_logs is True


def test_settings_normalize_log_level(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./textbook_agent.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-development-key")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("LESSON_BUILDER_PUBLIC_URL", "http://127.0.0.1:5173")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.log_level == "DEBUG"


def test_pytest_config_deselects_postgres_by_default() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    pytest_options = config["tool"]["pytest"]["ini_options"]

    assert "postgres: tests requiring a real PostgreSQL instance (deselected by default)" in pytest_options["markers"]
    assert "not postgres" in pytest_options["addopts"]
