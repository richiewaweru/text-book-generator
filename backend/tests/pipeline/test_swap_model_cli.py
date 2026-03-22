from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pipeline.cli import swap_model


def test_swap_model_cli_writes_slot_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_update_env_file(env_path: Path, updates: dict[str, str]) -> None:
        captured["env_path"] = env_path
        captured["updates"] = updates

    monkeypatch.setattr(swap_model, "update_env_file", fake_update_env_file)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "swap_model.py",
            "--slot",
            "fast",
            "--provider",
            "openai_compatible",
            "--model",
            "llama3-8b-8192",
            "--base-url",
            "https://api.groq.com/openai/v1",
            "--api-key-env",
            "GROQ_API_KEY",
        ],
    )

    swap_model.main()

    assert captured["env_path"] == (
        Path(swap_model.__file__).parent.parent.parent.parent / ".env"
    ).resolve()
    assert captured["updates"] == {
        "PIPELINE_FAST_PROVIDER": "openai_compatible",
        "PIPELINE_FAST_MODEL_NAME": "llama3-8b-8192",
        "PIPELINE_FAST_BASE_URL": "https://api.groq.com/openai/v1",
        "PIPELINE_FAST_API_KEY_ENV": "GROQ_API_KEY",
    }


def test_swap_model_cli_rejects_removed_route_alias(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "swap_model.py",
            "--route",
            "fast",
            "--provider",
            "anthropic",
            "--model",
            "claude-sonnet-4-6",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        swap_model.main()

    assert excinfo.value.code == 2
    assert "--route" in capsys.readouterr().err
