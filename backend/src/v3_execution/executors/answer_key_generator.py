from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from v3_execution.config.answer_key_node import effective_answer_key_node_name
from v3_execution.llm_helpers import run_json_agent
from v3_execution.models import (
    AnswerKeyExecutorWorkOrder,
    ExecutorOutcome,
    GeneratedAnswerKeyBlock,
)
from v3_execution.prompts.answer_key import build_answer_key_prompt
from v3_execution.config.retries import V3_MAX_RETRIES
from v3_execution.runtime.retry_runner import run_with_retries


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def execute_answer_key(
    order: AnswerKeyExecutorWorkOrder | None,
    emit_event: EmitFn,
    *,
    trace_id: str | None,
    generation_id: str | None,
    model_overrides: dict | None = None,
) -> GeneratedAnswerKeyBlock | None:
    if order is None:
        return None

    await emit_event("answer_key_started", {"generation_id": generation_id})

    async def _attempt(_: bool) -> ExecutorOutcome:
        prompt = build_answer_key_prompt(order)
        node_name = effective_answer_key_node_name(order)
        response = await run_json_agent(
            node_name=node_name,
            trace_id=trace_id,
            generation_id=generation_id,
            system_prompt="You output JSON only; never contradict provided answers.",
            user_prompt=prompt,
            model_overrides=model_overrides,
        )

        entries = response.get("entries") if isinstance(response, dict) else None
        if not isinstance(entries, list):
            return ExecutorOutcome(ok=False, errors=["answer key payload missing entries list"])

        include = set(order.answer_key_plan.include_question_ids)
        present = {entry.get("question_id") for entry in entries if isinstance(entry, dict)}
        errors = []
        missing = include - set(present)
        for mid in missing:
            errors.append(f"Answer key missing question {mid}")
        extra = set(present) - include
        for eid in extra:
            errors.append(f"Unexpected answer key row {eid}")

        for pq in order.questions:
            if pq.id not in include:
                continue
            matched = next(
                (
                    entry
                    for entry in entries
                    if isinstance(entry, dict) and entry.get("question_id") == pq.id
                ),
                None,
            )
            student_ans = str(matched.get("student_answer", "")).strip() if matched else ""
            if matched and pq.expected_answer.strip() not in student_ans:
                errors.append(f"Answer drift for question {pq.id}")

        ok = len(errors) == 0
        block = GeneratedAnswerKeyBlock(
            answer_key_id=str(uuid.uuid4()),
            style=order.answer_key_plan.style,
            entries=[e for e in entries if isinstance(e, dict)],
            source_work_order_id=order.work_order_id,
        )
        return ExecutorOutcome(ok=ok, blocks=[block], errors=errors)

    outcome = await run_with_retries(
        "answer-key",
        _attempt,
        max_retries=V3_MAX_RETRIES["answer_key_generator"],
    )
    block = next((b for b in outcome.blocks if isinstance(b, GeneratedAnswerKeyBlock)), None)
    if not outcome.ok or block is None:
        raise RuntimeError("; ".join(outcome.errors))

    await emit_event(
        "answer_key_ready",
        {
            "generation_id": generation_id,
            "style": block.style,
            "answer_key_id": block.answer_key_id,
        },
    )
    return block


__all__ = ["execute_answer_key"]
