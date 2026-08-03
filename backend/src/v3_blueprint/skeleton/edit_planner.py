"""LLM edit planner for Arm C — component/visual moves only."""

from __future__ import annotations

import json
import os
import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

from core.config import settings
from core.llm.runner import RetryPolicy, run_llm
from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from generation.v3_studio.prompts import build_v3_shared_prefix
from v3_blueprint.planning.models import LessonSkeleton
from v3_blueprint.skeleton.edits import (
    AddComponent,
    RemoveComponent,
    SetVisual,
    SkeletonEdit,
    SwapComponent,
)
from v3_execution.config import get_v3_model, get_v3_model_settings, get_v3_slot, get_v3_spec
from v3_execution.llm_helpers import structured_output_type_for_model

_CALLER = "v3_chunked_architect"
SKELETON_EDITOR_NODE = "v3_skeleton_editor"


class SkeletonEditPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edits: list[SwapComponent | AddComponent | RemoveComponent | SetVisual] = Field(
        default_factory=list
    )
    unexpressible: list[str] = Field(default_factory=list)


def _deviation_budget() -> int:
    raw = os.getenv("V3_SKELETON_DEVIATION_BUDGET", "4").strip()
    try:
        value = int(raw)
    except ValueError:
        return 4
    return max(0, value)


def build_skeleton_editor_system_prompt() -> str:
    shared_prefix = build_v3_shared_prefix()
    budget = _deviation_budget()
    return f"""{shared_prefix}
You propose a small number of typed edits to a computed lesson skeleton.

Section composition is FIXED. You must NOT add, drop, reorder, or duplicate sections.
You may only propose these edit kinds:
- swap_component
- add_component
- remove_component
- set_visual

Each edit must include a short reason.

If you wanted a structural change the vocabulary cannot express (for example a
second practice section, or a different section order), record it in
unexpressible. Do not invent illegal edits to approximate it.

Maximum edits: {budget}.

Output ONLY valid JSON:
{{
  "edits": [
    {{
      "kind": "swap_component",
      "section_id": "build",
      "from_slug": "explanation-block",
      "to_slug": "comparison-grid",
      "reason": "comparison teaches the contrast more clearly"
    }}
  ],
  "unexpressible": ["wanted a second practice section but shape is frozen"]
}}
"""


def build_skeleton_editor_user_message(
    *,
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    baseline: LessonSkeleton,
) -> str:
    return (
        f"Signals JSON:\n{signals.model_dump_json(indent=2)}\n\n"
        f"Form JSON:\n{form.model_dump_json(indent=2)}\n\n"
        f"BASELINE SKELETON JSON:\n{baseline.model_dump_json(indent=2)}\n\n"
        f"RESOURCE SPEC JSON:\n{json.dumps(resource_spec, indent=2, sort_keys=True)}"
    )


async def run_skeleton_edit_planner(
    *,
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    baseline: LessonSkeleton,
    generation_id: str | None = None,
    trace_id: str | None = None,
) -> SkeletonEditPlan:
    node = SKELETON_EDITOR_NODE
    tid = trace_id or generation_id or str(uuid.uuid4())
    model = get_v3_model(node)
    spec = get_v3_spec(node)
    slot = get_v3_slot(node)
    agent = Agent(
        model=model,
        output_type=structured_output_type_for_model(SkeletonEditPlan, spec=spec),
        system_prompt=build_skeleton_editor_system_prompt(),
    )
    try:
        result = await run_llm(
            trace_id=tid,
            caller=_CALLER,
            generation_id=generation_id,
            agent=agent,
            user_prompt=build_skeleton_editor_user_message(
                signals=signals,
                form=form,
                resource_spec=resource_spec,
                baseline=baseline,
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
        if isinstance(raw, SkeletonEditPlan):
            plan = raw
        elif hasattr(raw, "model_dump"):
            plan = SkeletonEditPlan.model_validate(raw.model_dump())
        else:
            plan = SkeletonEditPlan.model_validate(raw)
    except Exception as exc:
        print(
            f"[SKELETON EDITOR FALLBACK] generation_id={generation_id} error={exc}",
            flush=True,
        )
        return SkeletonEditPlan(edits=[], unexpressible=[f"editor_failed: {exc}"])

    budget = _deviation_budget()
    if len(plan.edits) > budget:
        overflow = plan.edits[budget:]
        plan = SkeletonEditPlan(
            edits=list(plan.edits[:budget]),
            unexpressible=[
                *plan.unexpressible,
                *[f"edit over budget dropped: {edit.kind}" for edit in overflow],
            ],
        )
    return plan


__all__ = [
    "SKELETON_EDITOR_NODE",
    "SkeletonEditPlan",
    "run_skeleton_edit_planner",
]
