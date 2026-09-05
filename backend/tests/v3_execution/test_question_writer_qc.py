from __future__ import annotations

import pytest

from v3_execution.executors import question_writer
from v3_execution.models import GeneratedQuestionBlock, QuestionWriterWorkOrder, WriterQuestion
from v3_execution.runtime.validation import validate_question_block


def _order(*questions: WriterQuestion) -> QuestionWriterWorkOrder:
    return QuestionWriterWorkOrder(
        work_order_id="q-practice",
        section_id="practice",
        questions=list(questions),
    )


def _block(question_id: str, text: str) -> GeneratedQuestionBlock:
    return GeneratedQuestionBlock(
        question_id=question_id,
        section_id="practice",
        difficulty="warm",
        data={"question": text},
        expected_answer="4",
        source_work_order_id="q-practice",
    )


def test_question_validation_rejects_drafting_residue() -> None:
    order = _order(WriterQuestion(id="q1", difficulty="warm", expected_answer="4"))

    residue_errors = validate_question_block(
        _block("q1", "Wait, adjust: actually solve the problem for the learner."),
        order,
    )

    assert any("drafting or self-correction" in error for error in residue_errors)


def test_question_validation_rejects_nested_question_residue_but_allows_normal_wording() -> None:
    order = _order(WriterQuestion(id="q1", difficulty="warm", expected_answer="4"))
    nested = _block("q1", "A valid top-level question")
    nested.data = {
        "problems": [
            {"question": "Choose a strategy or similar...", "solution": {"answer": "4"}}
        ]
    }
    valid = _block("q1", "What actually happens when the value doubles?")

    assert validate_question_block(nested, order)
    assert validate_question_block(valid, order) == []


@pytest.mark.asyncio
async def test_question_writer_retries_only_invalid_question_and_preserves_sibling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order(
        WriterQuestion(id="q1", difficulty="warm", expected_answer="4"),
        WriterQuestion(id="q2", difficulty="warm", expected_answer="6"),
    )
    responses = iter(
        [
            {
                "items": {
                    "q1": {"stem": "What is 2 + 2?"},
                    "q2": {"stem": "Wait, adjust: actually solve this problem..."},
                }
            },
            {"items": {"q2": {"stem": "What is 3 + 3?"}}},
        ]
    )
    prompts: list[str] = []

    async def fake_run_json_agent(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return next(responses)

    monkeypatch.setattr(question_writer, "run_json_agent", fake_run_json_agent)
    blocks = await question_writer.execute_questions(
        order,
        lambda *_args: _noop_emit(),
        trace_id="trace",
        generation_id="generation",
    )

    assert [(block.question_id, block.data["question"]) for block in blocks] == [
        ("q1", "What is 2 + 2?"),
        ("q2", "What is 3 + 3?"),
    ]
    assert len(prompts) == 2
    assert "self-correction residue" in prompts[1]


@pytest.mark.asyncio
async def test_component_question_writer_retries_text_residue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = QuestionWriterWorkOrder(
        work_order_id="items-practice",
        section_id="practice",
        component_id="practice-stack",
        section_field="practice",
        questions=[WriterQuestion(id="items-practice", difficulty="core", expected_answer="(pending)")],
    )
    responses = iter(
        [
            {
                "component_id": "practice-stack",
                "content": {
                    "problems": [
                        {"question": "Wait, adjust: actually solve this...", "solution": {"answer": "4"}}
                    ]
                },
            },
            {
                "component_id": "practice-stack",
                "content": {
                    "problems": [
                        {"question": "Solve this problem.", "solution": {"answer": "4"}}
                    ]
                },
            },
        ]
    )
    prompts: list[str] = []

    async def fake_run_json_agent(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return next(responses)

    monkeypatch.setattr(question_writer, "run_json_agent", fake_run_json_agent)
    blocks = await question_writer.execute_questions(
        order,
        lambda *_args: _noop_emit(),
        trace_id="trace",
        generation_id="generation",
    )

    assert blocks[0].data["problems"][0]["question"] == "Solve this problem."
    assert len(prompts) == 2
    assert "drafting or self-correction residue" in prompts[1]


@pytest.mark.asyncio
async def test_question_writer_keeps_one_retry_cap_after_batch_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order(WriterQuestion(id="q1", difficulty="warm", expected_answer="4"))
    responses = iter(
        [
            {"items": {"q1": {"stem": "Wait, adjust: actually solve this..."}}},
            {"items": {"q1": {"stem": "or similar..."}}},
        ]
    )
    calls = 0

    async def fake_run_json_agent(**_kwargs):
        nonlocal calls
        calls += 1
        return next(responses)

    monkeypatch.setattr(question_writer, "run_json_agent", fake_run_json_agent)
    with pytest.raises(RuntimeError):
        await question_writer.execute_questions(
            order,
            lambda *_args: _noop_emit(),
            trace_id="trace",
            generation_id="generation",
        )

    assert calls == 2


async def _noop_emit() -> None:
    return None
