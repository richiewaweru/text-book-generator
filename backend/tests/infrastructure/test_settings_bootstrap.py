from __future__ import annotations

import os

from textbook_agent.infrastructure.config.settings import bootstrap_environment


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

    loaded = bootstrap_environment(env_file)

    assert loaded == env_file
    assert os.getenv("ANTHROPIC_API_KEY") == "file-anthropic-key"
    assert os.getenv("PIPELINE_FAST_PROVIDER") == "anthropic"


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

    bootstrap_environment(env_file)

    assert os.getenv("LECTIO_CONTRACTS_DIR") == str(contracts_dir.resolve())
    assert os.getenv("DATABASE_URL") == f"sqlite+aiosqlite:///{(tmp_path / 'textbook_agent.db').resolve().as_posix()}"
