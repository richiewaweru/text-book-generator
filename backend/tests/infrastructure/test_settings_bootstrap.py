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
