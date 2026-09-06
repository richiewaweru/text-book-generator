from __future__ import annotations

import json
import uuid

from pydantic_ai import Agent

from core.config import settings
from core.llm.runner import RetryPolicy, run_llm
from core.prompts import effective_prompt_text
from generation.contracts import GenerationInputForm as V3InputForm
from generation.contracts import GenerationSignalSummary as V3SignalSummary
from generation.prompts import build_shared_generation_prefix
from v3_blueprint.planning.models import (
    IntentPlan,
    StructuralPlan,
    intent_plan_to_structural_plan,
)
from v3_blueprint.planning.validators import (
    _allowed_roles_from_resource_spec,
    validate_structural_plan_roles,
)
from v3_execution.config import get_v3_model, get_v3_model_settings, get_v3_slot, get_v3_spec
from v3_execution.llm_helpers import structured_output_type_for_model

_CALLER = "v3_chunked_architect"
STAGE1_NODE = "v3_stage1_planner"


def _load_stage1_static_body() -> str:
    return effective_prompt_text("structural-planner")


def build_stage1_system_prompt(*, path_prepared: bool = False) -> str:
    shared_prefix = build_shared_generation_prefix()
    static_body = _load_stage1_static_body()
    prompt = f"{shared_prefix}{static_body}"
    if not path_prepared:
        return prompt

    return prompt.replace(
        """  Give each card 2-4 misconceptions that are specific beliefs a learner would
  confidently act on, not slips, carelessness, or general confusion. If there
  is genuinely no known misconception, emit an empty list and set
  no_known_misconceptions=true. Never pad a list.""",
        """  Give each card ZERO to THREE misconceptions. Apply this test to every
  candidate: could a learner holding this belief confidently choose a corresponding wrong answer?
  If not, it is a knowledge gap, not a
  misconception. If there is genuinely no known misconception, emit an empty
  list and set no_known_misconceptions=true. Never pad a list.""",
    ).replace(
        """- A card has 2-4 real misconceptions, or explicitly sets
  no_known_misconceptions=true with an empty list.""",
        """- A card has 0-3 real misconceptions, or explicitly sets
  no_known_misconceptions=true with an empty list.""",
    )


def _intent_resource_spec_payload(resource_spec: dict) -> dict:
    """Strip component catalogues so Stage 1 cannot select components."""
    payload = {
        "resource_type": resource_spec.get("resource_type"),
        "depth": resource_spec.get("depth"),
        "rendered": resource_spec.get("rendered"),
    }
    raw_spec = resource_spec.get("spec")
    if not isinstance(raw_spec, dict):
        return payload

    sections = raw_spec.get("sections") if isinstance(raw_spec.get("sections"), dict) else {}
    stripped_sections: dict[str, list[dict]] = {}
    for group_name in ("required", "optional"):
        group = sections.get(group_name)
        if not isinstance(group, list):
            continue
        cleaned: list[dict] = []
        for section in group:
            if not isinstance(section, dict):
                continue
            cleaned.append(
                {
                    "role": section.get("role"),
                    "intent": section.get("intent"),
                    "max_count": section.get("max_count", 1),
                }
            )
        stripped_sections[group_name] = cleaned

    payload["spec"] = {
        "id": raw_spec.get("id"),
        "label": raw_spec.get("label"),
        "version": raw_spec.get("version"),
        "intent": raw_spec.get("intent"),
        "depth": raw_spec.get("depth"),
        "sections": stripped_sections,
        "validation": raw_spec.get("validation") or [],
    }
    return payload


def build_stage1_user_message(
    *,
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    skeleton_catalog: dict | None = None,
    previous_errors: list[str] | None = None,
) -> str:
    del skeleton_catalog  # Stage 1 role authority is the resource spec, not skeletons.
    intent_spec = _intent_resource_spec_payload(resource_spec)
    payload = (
        f"Signals JSON:\n{signals.model_dump_json(indent=2)}\n\n"
        f"Form JSON:\n{form.model_dump_json(indent=2)}\n\n"
        f"RESOURCE SPEC JSON (roles/intents only; no component catalogue):\n"
        f"{json.dumps(intent_spec, indent=2, sort_keys=True)}"
    )
    roles = sorted(_allowed_roles_from_resource_spec(resource_spec))
    if roles:
        payload += (
            "\n\nACTIVE RESOURCE SPEC ROLES (the only valid section roles):\n"
            + ", ".join(roles)
        )
    if previous_errors:
        payload += (
            "\n\nVALIDATION ERRORS FROM PREVIOUS ATTEMPT "
            "(fix all of these):\n"
            + "\n".join(f"- {error}" for error in previous_errors)
        )
    return payload


def _validate_stage1_roles(
    plan: StructuralPlan,
    resource_spec: dict | None,
) -> None:
    errors = validate_structural_plan_roles(plan, resource_spec=resource_spec)
    if errors:
        raise ValueError(errors[0])


async def _call_stage1(
    signals: V3SignalSummary,
    form: V3InputForm,
    resource_spec: dict,
    *,
    trace_id: str | None = None,
    generation_id: str | None = None,
    previous_errors: list[str] | None = None,
    skeleton_catalog: dict | None = None,
    path_prepared: bool = False,
) -> StructuralPlan:
    import traceback
    try:
        node = STAGE1_NODE
        tid = trace_id or generation_id or str(uuid.uuid4())
        model = get_v3_model(node)
        spec = get_v3_spec(node)
        slot = get_v3_slot(node)
        agent = Agent(
            model=model,
            output_type=structured_output_type_for_model(IntentPlan, spec=spec),
            system_prompt=build_stage1_system_prompt(path_prepared=path_prepared),
        )
        result = await run_llm(
            trace_id=tid,
            caller=_CALLER,
            generation_id=generation_id,
            agent=agent,
            user_prompt=build_stage1_user_message(
                signals=signals,
                form=form,
                resource_spec=resource_spec,
                skeleton_catalog=skeleton_catalog,
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
        if isinstance(raw, IntentPlan):
            intent = raw
        elif hasattr(raw, "model_dump"):
            intent = IntentPlan.model_validate(raw.model_dump())
        else:
            intent = IntentPlan.model_validate(raw)
        plan = intent_plan_to_structural_plan(intent)
        _validate_stage1_roles(plan, resource_spec)
        return plan
    except Exception as exc:
        tb = traceback.format_exc()
        print(
            f"\n[_CALL_STAGE1 ERROR]"
            f" generation_id={generation_id}"
            f" type={type(exc).__name__}"
            f"\nmessage={str(exc)}"
            f"\ntraceback:\n{tb}",
            flush=True,
        )
        raise


__all__ = [
    "STAGE1_NODE",
    "_call_stage1",
    "build_stage1_system_prompt",
    "build_stage1_user_message",
]
