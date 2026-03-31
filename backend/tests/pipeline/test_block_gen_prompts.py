from __future__ import annotations

import json

import pytest

from pipeline.contracts import clear_cache
from pipeline.prompts.block_gen import (
    build_block_system_prompt,
    build_block_user_prompt,
    get_edit_schema_fields,
)


@pytest.fixture(autouse=True)
def _clear_contract_cache():
    clear_cache()
    yield
    clear_cache()


def test_system_prompt_includes_capacity_and_hook_schema() -> None:
    text = build_block_system_prompt("hook-hero", None)
    assert "HookHero" in text or "hook" in text.lower()
    assert "headlineMaxWords" in text or "headline" in text
    assert "Output only valid JSON" in text


def test_system_prompt_unknown_component_raises() -> None:
    with pytest.raises(ValueError, match="Unknown component_id"):
        build_block_system_prompt("not-a-real-component", None)


def test_user_prompt_includes_context_and_existing() -> None:
    ctx = [{"component_id": "explanation-block", "content": {"body": "x", "emphasis": []}}]
    text = build_block_user_prompt(
        subject="Science",
        focus="Photosynthesis",
        grade_band="secondary",
        context_blocks=ctx,
        teacher_note="Keep it short",
        existing_content={"headline": "Old"},
    )
    assert "Science" in text
    assert "Photosynthesis" in text
    assert "Teacher instruction" in text
    assert "Existing content" in text
    assert "explanation-block" in text


def test_edit_schema_fields_for_hook_is_json_schema() -> None:
    schema = get_edit_schema_fields("hook-hero")
    assert "properties" in schema or "headline" in json.dumps(schema)
