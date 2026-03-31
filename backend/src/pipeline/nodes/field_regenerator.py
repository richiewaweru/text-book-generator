"""
field_regenerator node.

Regenerates a single failing field in an already-assembled section.
All other fields are preserved exactly as the model originally produced them.

STATE CONTRACT
    Reads:  current_section_id, generated_sections, assembled_sections,
            rerender_requests, contract
    Writes: generated_sections[sid] (field patched),
            assembled_sections[sid] (field patched),
            completed_nodes, errors
    Slot:   FAST - short targeted output, no need for STANDARD
    Skips:  if no rerender request for current_section_id
            if block_type is not in RETRYABLE_FIELDS
"""

from __future__ import annotations

import json

from pydantic_ai import Agent

from pipeline.llm_runner import run_llm
from pipeline.prompts.field_regen import (
    RETRYABLE_FIELDS,
    build_field_regen_system_prompt,
    build_field_regen_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.state import PipelineError, TextbookPipelineState


async def field_regenerator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    request = state.pending_rerender_for(sid)

    if request is None:
        return {"completed_nodes": ["field_regenerator"]}

    if request.block_type not in RETRYABLE_FIELDS:
        return {"completed_nodes": ["field_regenerator"]}

    section = state.generated_sections.get(sid)
    if section is None:
        return {
            "errors": [
                PipelineError(
                    node="field_regenerator",
                    section_id=sid,
                    message=f"No generated content found for {sid}",
                    recoverable=False,
                )
            ],
            "completed_nodes": ["field_regenerator"],
        }

    model = get_node_text_model(
        "field_regenerator",
        model_overrides=model_overrides,
    )

    agent = Agent(
        model=model,
        output_type=str,
        system_prompt=build_field_regen_system_prompt(state.contract.id),
    )

    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="field_regenerator",
            agent=agent,
            model=model,
            user_prompt=build_field_regen_user_prompt(
                section=section,
                failing_field=request.block_type,
                reason=request.reason,
            ),
            section_id=sid,
        )

        raw_field = json.loads(result.output)
        patched_payload = section.model_dump(exclude_none=True)
        patched_payload[request.block_type] = raw_field
        patched_section = type(section).model_validate(patched_payload)

        return {
            "generated_sections": {**state.generated_sections, sid: patched_section},
            "assembled_sections": {**state.assembled_sections, sid: patched_section},
            "completed_nodes": ["field_regenerator"],
        }

    except json.JSONDecodeError as exc:
        return {
            "errors": [
                PipelineError(
                    node="field_regenerator",
                    section_id=sid,
                    message=f"Failed to parse regenerated field JSON: {exc}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["field_regenerator"],
        }
    except Exception as exc:
        return {
            "errors": [
                PipelineError(
                    node="field_regenerator",
                    section_id=sid,
                    message=f"Field regeneration failed: {exc}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["field_regenerator"],
        }
