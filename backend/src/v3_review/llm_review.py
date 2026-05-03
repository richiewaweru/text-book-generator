from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from core.llm.runner import run_llm
from v3_blueprint.models import ProductionBlueprint
from v3_execution.config import get_v3_model, get_v3_slot, get_v3_spec
from v3_execution.models import DraftPack

from v3_review.models import ReviewIssue
from v3_review.prompts import COHERENCE_SYSTEM_PROMPT, build_llm_review_user_prompt

_NODE = "v3_coherence_reviewer"
_CALLER = "v3_review"


class LLMReviewEnvelope(BaseModel):
    model_config = {"extra": "forbid"}

    issues: list[ReviewIssue] = Field(default_factory=list)


async def run_llm_review(
    blueprint: ProductionBlueprint,
    draft_pack: DraftPack,
    deterministic_issues: list[ReviewIssue],
    *,
    trace_id: str | None,
    generation_id: str | None,
    model_overrides: dict | None = None,
) -> list[ReviewIssue]:
    det_json = [i.model_dump(mode="json") for i in deterministic_issues]
    user_prompt = build_llm_review_user_prompt(blueprint, draft_pack, det_json)

    model = get_v3_model(_NODE, model_overrides=model_overrides)
    spec = get_v3_spec(_NODE)
    slot = get_v3_slot(_NODE)

    agent = Agent(
        model=model,
        output_type=LLMReviewEnvelope,
        system_prompt=COHERENCE_SYSTEM_PROMPT,
    )
    try:
        result = await run_llm(
            trace_id=trace_id or generation_id or "v3-coherence",
            caller=_CALLER,
            generation_id=generation_id,
            agent=agent,
            user_prompt=user_prompt,
            model=model,
            slot=slot,
            spec=spec,
            section_id=None,
            node=_NODE,
        )
    except (RuntimeError, ValueError, TypeError):
        return []

    raw = result.output
    if hasattr(raw, "issues"):
        return list(raw.issues)  # type: ignore[no-any-return]
    if isinstance(raw, LLMReviewEnvelope):
        return list(raw.issues)
    return []


__all__ = ["run_llm_review"]
