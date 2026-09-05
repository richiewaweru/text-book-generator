from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from v3_execution.llm_helpers import run_json_agent
from v3_execution.models import ExecutorOutcome, GeneratedQuestionBlock, QuestionWriterWorkOrder
from v3_execution.prompts.question_writer import build_question_writer_prompt
from v3_execution.config.retries import V3_MAX_RETRIES
from v3_execution.runtime.retry_runner import run_with_retries
from v3_execution.runtime.validation import (
    validate_question_batch,
    validate_question_content,
    validate_question_block,
)


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


def _items_map(payload: dict[str, Any]) -> dict[str, Any]:
    if "items" in payload and isinstance(payload["items"], dict):
        return payload["items"]
    return payload


def _extract_component_content(
    response: dict[str, Any],
    *,
    component_id: str,
) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise RuntimeError("question writer returned non-object JSON")
    claimed = response.get("component_id")
    if claimed is not None and claimed != component_id:
        raise RuntimeError(
            f"Writer attempted to change component_id from '{component_id}' to '{claimed}'"
        )
    content = response.get("content")
    if isinstance(content, dict):
        return content
    # Allow bare Lectio objects when the model omits the envelope.
    if "items" not in response:
        return dict(response)
    raise RuntimeError(
        f"Component-aware question writer must return content for {component_id}, "
        "not a generic items wrapper"
    )


async def execute_questions(
    order: QuestionWriterWorkOrder,
    emit_event: EmitFn,
    *,
    trace_id: str | None,
    generation_id: str | None,
    model_overrides: dict | None = None,
) -> list[GeneratedQuestionBlock]:
    await emit_event(
        "questions_started",
        {"section_id": order.section_id, "generation_id": generation_id},
    )

    async def _call(
        attempt_order: QuestionWriterWorkOrder,
        *,
        correction_hint: str | None = None,
    ) -> dict[str, Any]:
        prompt = build_question_writer_prompt(
            attempt_order,
            correction_hint=correction_hint,
        )
        response = await run_json_agent(
            node_name="v3_question_writer",
            trace_id=trace_id,
            generation_id=generation_id,
            system_prompt="You output JSON only.",
            user_prompt=prompt,
            model_overrides=model_overrides,
        )
        return response

    def _standard_blocks(
        response: dict[str, Any],
        attempt_order: QuestionWriterWorkOrder,
    ) -> tuple[list[GeneratedQuestionBlock], list[str]]:
        bucket = _items_map(response)
        blocks: list[GeneratedQuestionBlock] = []
        errors: list[str] = []

        for planned in attempt_order.questions:
            entry = bucket.get(planned.id)
            if entry is None:
                errors.append(f"Missing stem for question {planned.id}")
                continue
            stem = entry.get("stem") if isinstance(entry, dict) else str(entry)

            block = GeneratedQuestionBlock(
                question_id=planned.id,
                section_id=attempt_order.section_id,
                difficulty=planned.difficulty,
                data={
                    "question": stem,
                    "difficulty": planned.difficulty,
                    "hints": [],
                },
                expected_answer=planned.expected_answer,
                expected_working=planned.expected_working,
                diagram_required=planned.diagram_required,
                source_work_order_id=attempt_order.work_order_id,
            )
            blocks.append(block)

        errors.extend(validate_question_batch(blocks, attempt_order))
        return blocks, errors

    component_prior_errors: list[str] = []

    async def _component_attempt(already_retried: bool) -> ExecutorOutcome:
        response = await _call(
            order,
            correction_hint=(
                "\n".join(component_prior_errors)
                if already_retried
                else None
            ),
        )

        if order.component_id:
            content = _extract_component_content(response, component_id=order.component_id)
            planned = order.questions[0] if order.questions else None
            question_id = planned.id if planned else order.work_order_id
            expected = planned.expected_answer if planned else ""
            difficulty = planned.difficulty if planned else "core"
            # Prefer solution.answer / quiz correct option when present.
            if isinstance(content.get("problems"), list) and content["problems"]:
                first = content["problems"][0]
                if isinstance(first, dict):
                    solution = first.get("solution") if isinstance(first.get("solution"), dict) else {}
                    if solution.get("answer"):
                        expected = str(solution["answer"])
                    if first.get("difficulty"):
                        difficulty = str(first["difficulty"])
            elif isinstance(content.get("options"), list):
                for option in content["options"]:
                    if isinstance(option, dict) and option.get("correct") is True:
                        expected = str(option.get("text") or expected)
                        break
            block = GeneratedQuestionBlock(
                question_id=question_id,
                section_id=order.section_id,
                difficulty=difficulty,
                data=content,
                expected_answer=expected,
                expected_working=planned.expected_working if planned else None,
                diagram_required=planned.diagram_required if planned else False,
                source_work_order_id=order.work_order_id,
            )
            errors = validate_question_content(block.data, question_id=question_id)
            component_prior_errors[:] = errors
            return ExecutorOutcome(ok=not errors, blocks=[block], errors=errors)

        raise AssertionError("component attempt called for a non-component order")

    if order.component_id:
        outcome = await run_with_retries(
            f"questions:{order.section_id}",
            _component_attempt,
            # Component-aware output is one whole block: allow only the existing
            # initial attempt plus one correction attempt.
            max_retries=min(1, V3_MAX_RETRIES["question_writer"]),
        )
    else:
        # Generate the batch once, then retry only malformed/missing questions. This
        # keeps valid siblings stable and retains the existing one-retry-per-block cap.
        initial_response = await _call(order)
        initial_blocks, initial_errors = _standard_blocks(initial_response, order)
        blocks_by_id = {block.question_id: block for block in initial_blocks}
        errors_by_id: dict[str, list[str]] = {question.id: [] for question in order.questions}
        for block in initial_blocks:
            errors_by_id[block.question_id].extend(
                validate_question_block(block, order)
            )
        for question in order.questions:
            if question.id not in blocks_by_id:
                errors_by_id[question.id].append(
                    f"Missing stem for question {question.id}"
                )

        failed_ids = [question.id for question in order.questions if errors_by_id[question.id]]
        known_block_errors = {
            error for question_errors in errors_by_id.values() for error in question_errors
        }
        batch_only_errors = [
            error for error in initial_errors if error not in known_block_errors
        ]
        if not failed_ids and not batch_only_errors:
            outcome = ExecutorOutcome(ok=True, blocks=initial_blocks, errors=[])
        elif batch_only_errors:
            outcome = ExecutorOutcome(
                ok=False,
                blocks=initial_blocks,
                errors=batch_only_errors,
            )
        else:
            final_blocks: dict[str, GeneratedQuestionBlock] = {
                block.question_id: block
                for block in initial_blocks
                if not errors_by_id[block.question_id]
            }
            retry_errors: list[str] = []
            for question in order.questions:
                question_errors = errors_by_id[question.id]
                if not question_errors:
                    continue
                retry_order = order.model_copy(update={"questions": [question]})

                async def _retry(
                    _: bool,
                    *,
                    _order=retry_order,
                    _errors=question_errors,
                ) -> ExecutorOutcome:
                    response = await _call(_order, correction_hint="\n".join(_errors))
                    retry_blocks, errors = _standard_blocks(response, _order)
                    return ExecutorOutcome(ok=not errors, blocks=retry_blocks, errors=errors)

                retry_budget = V3_MAX_RETRIES["question_writer"]
                if retry_budget:
                    # The initial batch call already consumed the first attempt for
                    # this question; only the remaining retry budget belongs here.
                    retried = await run_with_retries(
                        f"question:{question.id}",
                        _retry,
                        max_retries=max(0, retry_budget - 1),
                    )
                else:
                    retried = ExecutorOutcome(
                        ok=False,
                        blocks=[],
                        errors=question_errors,
                    )
                if retried.ok:
                    final_blocks[question.id] = retried.blocks[0]
                else:
                    retry_errors.extend(retried.errors)
            outcome = ExecutorOutcome(
                ok=not retry_errors,
                blocks=[final_blocks[q.id] for q in order.questions if q.id in final_blocks],
                errors=retry_errors,
            )
    if not outcome.ok:
        raise RuntimeError("; ".join(outcome.errors))

    emitted: list[GeneratedQuestionBlock] = []
    for block in outcome.blocks:
        if not isinstance(block, GeneratedQuestionBlock):
            continue
        emitted.append(block)
        await emit_event(
            "question_ready",
            {
                "generation_id": generation_id,
                "question_id": block.question_id,
                "section_id": block.section_id,
                "difficulty": block.difficulty,
                "data": block.data,
            },
        )
    return emitted


__all__ = ["execute_questions"]
