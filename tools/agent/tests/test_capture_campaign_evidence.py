from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from tools.agent.capture_campaign_evidence import (
    capture_campaign_evidence,
    generation_steps,
    generations,
    llm_calls,
    metadata,
)


@pytest.fixture
def campaign_database(tmp_path):
    database_path = tmp_path / "campaign.sqlite"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    asyncio.run(_create_campaign_database(database_url))
    return database_url


async def _create_campaign_database(database_url):
    engine = create_async_engine(database_url)
    try:
        now = datetime(2026, 9, 4, 9, 30, tzinfo=timezone.utc)
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
            await connection.execute(
                generations.insert().values(
                    id="generation-001",
                    subject="Science",
                    mode="balanced",
                    status="completed",
                    requested_template_id="guided-concept-path",
                    resolved_template_id="guided-concept-path",
                    requested_preset_id="default",
                    resolved_preset_id="default",
                    section_count=3,
                    quality_passed=True,
                    generation_time_seconds=12.5,
                    chunked_state_json={
                        "stage": "complete",
                        "selection_trace": [
                            {
                                "section_id": "section-1",
                                "role": "model",
                                "intent": "A labeled visual is required.",
                                "candidate_set": ["diagram-block", "callout-block"],
                                "budget_before": {"diagram-block": 1},
                                "selected": [
                                    {
                                        "component_id": "diagram-block",
                                        "purpose": "Show the concept.",
                                        "reason": "A labeled visual is required.",
                                        "block_id": "section-1-diagram",
                                        "lane": "visual",
                                        "section_field": "diagram",
                                        "prompt": "do not export this prompt",
                                    }
                                ],
                                "budget_pressure": "none",
                                "legal": True,
                                "raw_error": "do not export this raw error",
                                "api_key": "super-secret",
                            }
                        ],
                        "document": {"title": "full lesson must not be exported"},
                    },
                    created_at=now,
                    completed_at=now,
                    last_heartbeat=now,
                )
            )
            await connection.execute(
                generation_steps.insert(),
                [
                    {
                        "id": "step-b",
                        "generation_id": "generation-001",
                        "part_id": "block-1",
                        "variant_id": "everyone",
                        "step": "block_ready",
                        "kind": "lesson",
                        "payload": {
                            "attempt": 2,
                            "recovery_action": "repair",
                            "component_id": "diagram-block",
                            "payload": {"text": "full lesson content"},
                            "prompt": "private prompt",
                        },
                        "created_at": now,
                    },
                    {
                        "id": "step-a",
                        "generation_id": "generation-001",
                        "part_id": "block-1",
                        "variant_id": "everyone",
                        "step": "block_failed",
                        "kind": "lesson",
                        "payload": {
                            "attempt": 1,
                            "error": {
                                "class": "provider_transient",
                                "message": "response included private lesson content",
                                "validation_errors": ["private content"],
                            },
                        },
                        "created_at": now,
                    },
                ],
            )
            await connection.execute(
                llm_calls.insert().values(
                    id="call-1",
                    trace_id="trace-1",
                    generation_id="generation-001",
                    caller="component_lectio",
                    node="visual_writer",
                    slot="visual",
                    family="xai",
                    model_name="grok-example",
                    endpoint_host="https://user:password@api.example.test/v1?key=secret",
                    section_id="section-1",
                    attempt=1,
                    status="success",
                    retryable=False,
                    latency_ms=123.0,
                    tokens_in=50,
                    tokens_out=75,
                    thinking_tokens=5,
                    cost_usd=0.012,
                    started_at=now,
                    completed_at=now,
                    created_at=now,
                )
            )
    finally:
        await engine.dispose()


def test_capture_writes_sanitized_json_and_markdown(campaign_database, tmp_path):
    json_path, markdown_path = asyncio.run(
        capture_campaign_evidence(
            database_url=campaign_database,
            generation_id="generation-001",
            campaign_run_id="L01",
            environment="local",
            commit_sha="8509233",
            output_dir=tmp_path / "evidence",
        )
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload)

    assert payload["generation"]["stage"] == "complete"
    trace = payload["generation"]["selection_trace"]
    assert trace[0]["selected"][0]["component_id"] == "diagram-block"
    assert "prompt" not in trace[0]["selected"][0]
    assert "raw_error" not in trace[0]
    assert "api_key" not in trace[0]
    assert [step["id"] for step in payload["generation_steps"]] == ["step-a", "step-b"]
    assert payload["generation_steps"][1]["metadata"] == {
        "attempt": 2,
        "component_id": "diagram-block",
        "recovery_action": "repair",
    }
    assert payload["generation_steps"][0]["metadata"]["error"] == {"class": "provider_transient"}
    assert payload["llm_calls"][0]["endpoint_host"] == "api.example.test"
    assert "super-secret" not in serialized
    assert "private prompt" not in serialized
    assert "full lesson content" not in serialized
    assert "response included" not in serialized

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Status / stage | completed / complete" in markdown
    assert "Ordered generation steps: 2" in markdown
    assert "LLM calls: 1" in markdown


def test_capture_rejects_unknown_generation(campaign_database, tmp_path):
    with pytest.raises(ValueError, match="Generation not found"):
        asyncio.run(
            capture_campaign_evidence(
                database_url=campaign_database,
                generation_id="missing",
                campaign_run_id="L02",
                environment="local",
                commit_sha="8509233",
                output_dir=tmp_path,
            )
        )


def test_capture_rejects_path_like_campaign_run_id(campaign_database, tmp_path):
    with pytest.raises(ValueError, match="campaign_run_id"):
        asyncio.run(
            capture_campaign_evidence(
                database_url=campaign_database,
                generation_id="generation-001",
                campaign_run_id="../L03",
                environment="local",
                commit_sha="8509233",
                output_dir=tmp_path,
            )
        )
