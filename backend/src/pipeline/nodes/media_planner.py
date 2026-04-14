from __future__ import annotations

from pipeline.media.planner.media_planner import media_planner as build_media_plan
from pipeline.state import TextbookPipelineState


async def media_planner(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    _ = model_overrides
    typed = TextbookPipelineState.parse(state)
    sid = typed.current_section_id
    section = typed.generated_sections.get(sid)
    if sid is None or section is None or typed.current_section_plan is None:
        return {"completed_nodes": ["media_planner"]}

    plan = build_media_plan(
        section_plan=typed.current_section_plan,
        section_content=section,
        template_contract=typed.contract,
        style_context=typed.style_context,
    )
    return {
        "media_plans": {sid: plan},
        "media_lifecycle": {sid: "planned"},
        "completed_nodes": ["media_planner"],
    }


__all__ = ["media_planner"]
