from __future__ import annotations

from pipeline.prompts.qc import build_qc_user_prompt


def test_qc_prompt_includes_pack_objective() -> None:
    prompt = build_qc_user_prompt(
        section_json='{"section_id": "s1"}',
        selected_components=["explanation-block"],
        section_role="explain",
        pack_objective="Students can calculate slope.",
    )
    assert "Pack objective: Students can calculate slope." in prompt
    assert "explanation-block" in prompt

