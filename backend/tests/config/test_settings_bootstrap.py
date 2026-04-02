from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from core.config import Settings, bootstrap_environment
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
