from __future__ import annotations

import os

from core.config import bootstrap_environment


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
