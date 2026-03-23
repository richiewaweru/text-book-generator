"""
content_generator node.

Produces a SectionContent object per section.
Slot assignment is resolved centrally as STANDARD.
"""

from __future__ import annotations

from pydantic import ValidationError
from pydantic_ai import Agent

from pipeline.prompts.content import (
    build_content_system_prompt,
    build_content_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.types.section_content import SectionContent
from pipeline.llm_runner import run_llm


def _seed_section(state: TextbookPipelineState, section_id: str | None) -> SectionContent | None:
    """Return the matching seeded section so rerenders can preserve intent."""

    if section_id is None or state.request.seed_document is None:
        return None
    for section in state.request.seed_document.sections:
        if section.section_id == section_id:
            return section
    return None


async def content_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Generate or rerender one section's core teaching content."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    plan = state.current_section_plan

    rerender_request = state.pending_rerender_for(sid)
    rerender_reason = rerender_request.reason if rerender_request else None

    is_rerender = rerender_reason is not None
    seed_section = _seed_section(state, sid)
    seed_note = state.request.seed_document.note if state.request.seed_document else None

    model = get_node_text_model(
        "content_generator",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=SectionContent,
        system_prompt=build_content_system_prompt(
            template_id=state.contract.id,
            template_name=state.contract.name,
            template_family=state.contract.family,
        ),
    )

    generated = dict(state.generated_sections)
    errors = []

    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="content_generator",
            agent=agent,
            model=model,
            user_prompt=build_content_user_prompt(
                section_plan=plan,
                subject=state.request.subject,
                context=state.request.context,
                grade_band=state.request.grade_band,
                learner_fit=state.request.learner_fit,
                template_id=state.contract.id,
                rerender_reason=rerender_reason,
                seed_section=seed_section,
                seed_note=seed_note,
            ),
            section_id=sid,
            generation_mode=state.request.mode,
        )
        generated[sid] = result.output
    except ValidationError as exc:
        errors.append(
            PipelineError(
                node="content_generator",
                section_id=sid,
                message=(
                    f"Schema validation failed: {exc.error_count()} errors. "
                    f"First: {exc.errors()[0]['msg']}"
                ),
                recoverable=True,
            )
        )
    except Exception as exc:
        errors.append(
            PipelineError(
                node="content_generator",
                section_id=sid,
                message=f"LLM call failed: {exc}",
                recoverable=True,
            )
        )

    new_rerender_count = dict(state.rerender_count)
    if is_rerender and sid:
        new_rerender_count[sid] = state.rerender_count.get(sid, 0) + 1

    output: dict = {
        "generated_sections": generated,
        "rerender_count": new_rerender_count,
        "completed_nodes": ["content_generator"],
    }
    if errors:
        output["errors"] = errors

    return output
