from __future__ import annotations

import json
import uuid

from pydantic_ai import Agent

from core.config import settings
from core.llm.runner import RetryPolicy, run_llm
from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from generation.v3_studio.prompts import _planner_index_block, build_v3_shared_prefix
from v3_blueprint.planning.models import LessonSkeleton, Stage0SkeletonFailure
from v3_blueprint.planning.validators import (
    _allowed_roles_from_resource_spec,
    validate_lesson_skeleton,
)
from v3_execution.config import get_v3_model, get_v3_model_settings, get_v3_slot, get_v3_spec
from v3_execution.llm_helpers import structured_output_type_for_model

_CALLER = "v3_chunked_architect"
STAGE0_NODE = "v3_stage0_skeleton"


def build_stage0_system_prompt() -> str:
    shared_prefix = build_v3_shared_prefix()
    planner_block = _planner_index_block()

    return f"""{shared_prefix}
You are a lesson structure planner. Produce only valid LessonSkeleton JSON.

You decide lesson_mode and the section sequence with component slugs only.
You do NOT write goals, anchors, voice, purposes, pitfalls, or question text.

{planner_block}

CONSTRAINT: Each section_field (shown in brackets) may appear at most once per section.
Never plan two components with the same section_field in the same section.

REASONING STEPS — work through these in order before producing JSON

STEP 1 — MODE
  Restate lesson_mode from the signals. Do not re-derive it.

STEP 2 — SPEC GATE
  Read the resource spec. State required roles and forbidden components.
  Remove anything the spec forbids before continuing.

STEP 3 — SECTION SEQUENCE
  List sections in order: all required roles plus any optional roles that fit
  within the depth envelope.
  Emit role using the exact role strings allowed by the active resource spec.
  Choose a short title for each section.
  Mark visual_required only where the concept needs spatial or relational structure.

STEP 4 — SLOT MAPPING
  For each section, choose components only from that role's preferred or allowed
  set in the resource spec.
  Never use a forbidden component.
  No two components may share a section_field within one section.
  Max 4 components per section.

STEP 5 — SELF CHECK
  Verify:
  - every emitted role exists in the active resource spec
  - no two components in any section share a section_field
  - visual_required sections include a visual-capable component
  - section count respects the resource spec depth limits

Output ONLY valid JSON matching this schema exactly:
{{
  "lesson_mode": "first_exposure",
  "sections": [
    {{
      "id": "intro",
      "title": "What do you already know about sharing equally?",
      "role": "intro",
      "visual_required": false,
      "components": [
        {{ "slug": "hook-hero" }}
      ]
    }}
  ]
}}

HARD RULES:
- Only use slugs from AVAILABLE COMPONENTS. Never invent slugs.
- Max 6 sections.
- Max 4 component slugs per section.
- Every emitted role must exist in the active resource spec.
- Do not include purposes, transition_notes, content_intent, or question text.
- Do not add any JSON keys not shown in the schema above.
"""


def build_stage0_user_message(
    *,
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    previous_errors: list[str] | None = None,
) -> str:
    payload = (
        f"Signals JSON:\n{signals.model_dump_json(indent=2)}\n\n"
        f"Form JSON:\n{form.model_dump_json(indent=2)}\n\n"
        f"RESOURCE SPEC JSON:\n{json.dumps(resource_spec, indent=2, sort_keys=True)}"
    )
    if previous_errors:
        payload += (
            "\n\nVALIDATION ERRORS FROM PREVIOUS ATTEMPT "
            "(fix all of these):\n"
            + "\n".join(f"- {error}" for error in previous_errors)
        )
    return payload


def _validate_stage0_roles(skeleton: LessonSkeleton, resource_spec: dict) -> None:
    allowed_roles = _allowed_roles_from_resource_spec(resource_spec)
    if not allowed_roles:
        return
    for section in skeleton.sections:
        if section.role not in allowed_roles:
            raise ValueError(
                f"Section '{section.id}' emitted role '{section.role}' "
                f"which is not in the active resource spec roles: {sorted(allowed_roles)}."
            )


async def _call_stage0(
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    *,
    trace_id: str | None = None,
    generation_id: str | None = None,
    previous_errors: list[str] | None = None,
) -> LessonSkeleton:
    import traceback

    try:
        node = STAGE0_NODE
        tid = trace_id or generation_id or str(uuid.uuid4())
        model = get_v3_model(node)
        spec = get_v3_spec(node)
        slot = get_v3_slot(node)
        agent = Agent(
            model=model,
            output_type=structured_output_type_for_model(LessonSkeleton, spec=spec),
            system_prompt=build_stage0_system_prompt(),
        )
        result = await run_llm(
            trace_id=tid,
            caller=_CALLER,
            generation_id=generation_id,
            agent=agent,
            user_prompt=build_stage0_user_message(
                signals=signals,
                form=form,
                resource_spec=resource_spec,
                previous_errors=previous_errors,
            ),
            model=model,
            slot=slot,
            spec=spec,
            section_id=None,
            node=node,
            model_settings=get_v3_model_settings(node),
            retry_policy=RetryPolicy(
                max_attempts=1,
                call_timeout_seconds=float(settings.v3_timeout_stage1_seconds),
            ),
        )
        raw = result.output
        if isinstance(raw, LessonSkeleton):
            skeleton = raw
        elif hasattr(raw, "model_dump"):
            skeleton = LessonSkeleton.model_validate(raw.model_dump())
        else:
            skeleton = LessonSkeleton.model_validate(raw)
        _validate_stage0_roles(skeleton, resource_spec)
        errors = validate_lesson_skeleton(skeleton, resource_spec)
        if errors:
            print(
                f"[STAGE0 SKELETON INVALID] generation_id={generation_id} errors={errors}",
                flush=True,
            )
            raise Stage0SkeletonFailure(errors=errors)
        return skeleton
    except Stage0SkeletonFailure:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        print(
            f"\n[_CALL_STAGE0 ERROR]"
            f" generation_id={generation_id}"
            f" type={type(exc).__name__}"
            f"\nmessage={str(exc)}"
            f"\ntraceback:\n{tb}",
            flush=True,
        )
        raise


__all__ = [
    "STAGE0_NODE",
    "_call_stage0",
    "build_stage0_system_prompt",
    "build_stage0_user_message",
]
