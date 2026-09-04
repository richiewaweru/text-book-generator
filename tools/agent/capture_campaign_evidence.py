"""Capture sanitized, read-only database evidence for one generation.

Usage::

    python tools/agent/capture_campaign_evidence.py \
        --generation-id <generation-id> --campaign-run-id CL-LOCAL-001 \
        --environment local --commit-sha <sha> \
        --output-dir artifacts/live-verification/runs

The database URL comes from the configured backend settings. The command only
issues SELECT statements. It deliberately excludes prompts, lesson/document
content, user identifiers, and raw error messages from its JSON and Markdown
outputs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.agent.common import REPO_ROOT


SCHEMA_VERSION = 1
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SAFE_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
_STEP_METADATA_KEYS = frozenset(
    {
        "attempt",
        "block_id",
        "component_id",
        "correction_hint",
        "lane",
        "max_attempts",
        "plan_hash",
        "plan_revision",
        "reasons",
        "recovered_from",
        "recovery",
        "recovery_action",
        "retryable",
        "section_id",
        "status",
    }
)
_ERROR_METADATA_KEYS = frozenset({"attempt", "class", "code", "retryable", "type"})
_SELECTION_TRACE_KEYS = frozenset(
    {
        "section_id",
        "role",
        "intent",
        "candidate_set",
        "budget_before",
        "selected",
        "budget_pressure",
        "legal",
    }
)
_SELECTED_TRACE_KEYS = frozenset(
    {
        "component_id",
        "purpose",
        "reason",
        "block_id",
        "lane",
        "section_field",
    }
)
_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "authorization",
    "content",
    "document",
    "instruction",
    "password",
    "prompt",
    "response",
    "secret",
    "token",
)

metadata = MetaData()
generations = Table(
    "generations",
    metadata,
    Column("id", String, primary_key=True),
    Column("subject", String),
    Column("mode", String),
    Column("status", String),
    Column("error_type", String),
    Column("error_code", String),
    Column("requested_template_id", String),
    Column("resolved_template_id", String),
    Column("requested_preset_id", String),
    Column("resolved_preset_id", String),
    Column("section_count", Integer),
    Column("quality_passed", Boolean),
    Column("generation_time_seconds", Float),
    Column("chunked_state_json", JSON),
    Column("created_at", DateTime),
    Column("completed_at", DateTime),
    Column("last_heartbeat", DateTime),
)
generation_steps = Table(
    "generation_steps",
    metadata,
    Column("id", String, primary_key=True),
    Column("generation_id", String),
    Column("part_id", String),
    Column("variant_id", String),
    Column("step", String),
    Column("kind", String),
    Column("payload", JSON),
    Column("created_at", DateTime),
)
llm_calls = Table(
    "llm_calls",
    metadata,
    Column("id", String, primary_key=True),
    Column("trace_id", String),
    Column("generation_id", String),
    Column("caller", String),
    Column("node", String),
    Column("slot", String),
    Column("family", String),
    Column("model_name", String),
    Column("endpoint_host", String),
    Column("section_id", String),
    Column("attempt", Integer),
    Column("status", String),
    Column("retryable", Boolean),
    Column("latency_ms", Float),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    Column("thinking_tokens", Integer),
    Column("cost_usd", Float),
    Column("started_at", DateTime),
    Column("completed_at", DateTime),
    Column("created_at", DateTime),
)


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    """Keep bounded metadata while removing content-bearing or secret-bearing keys."""
    if depth > 6:
        return "[truncated]"
    if isinstance(value, Mapping):
        return {
            str(key): _safe_value(item, depth=depth + 1)
            for key, item in value.items()
            if not any(fragment in str(key).lower() for fragment in _SENSITIVE_KEY_FRAGMENTS)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return value[:500]
    return _json_value(value)


def _selection_trace(chunked_state: Any) -> Any:
    if not isinstance(chunked_state, Mapping):
        return None
    trace = chunked_state.get("selection_trace")
    if not isinstance(trace, list):
        return None
    sanitized: list[dict[str, Any]] = []
    for entry in trace[:100]:
        if not isinstance(entry, Mapping):
            continue
        item = {
            key: _safe_value(entry[key])
            for key in _SELECTION_TRACE_KEYS - {"selected"}
            if key in entry
        }
        selected = entry.get("selected")
        if isinstance(selected, list):
            item["selected"] = [
                {
                    key: _safe_value(choice[key])
                    for key in _SELECTED_TRACE_KEYS
                    if key in choice
                }
                for choice in selected[:100]
                if isinstance(choice, Mapping)
            ]
        sanitized.append(item)
    return sanitized


def _stage(chunked_state: Any) -> str | None:
    if not isinstance(chunked_state, Mapping):
        return None
    stage = chunked_state.get("stage")
    return str(stage)[:100] if stage is not None else None


def _step_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    result = {key: _safe_value(payload[key]) for key in _STEP_METADATA_KEYS if key in payload}
    error = payload.get("error")
    if isinstance(error, Mapping):
        result["error"] = {
            key: _safe_value(error[key]) for key in _ERROR_METADATA_KEYS if key in error
        }
    return result


def _endpoint_host(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value)
    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    return parsed.hostname


def _mapping(row: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: _json_value(row[key]) for key in keys}


async def collect_campaign_evidence(
    connection: AsyncConnection,
    *,
    generation_id: str,
    campaign_run_id: str,
    environment: str,
    commit_sha: str,
) -> dict[str, Any]:
    """Read and sanitize evidence for one generation using an existing connection."""
    generation_result = await connection.execute(
        select(
            generations.c.id,
            generations.c.subject,
            generations.c.mode,
            generations.c.status,
            generations.c.error_type,
            generations.c.error_code,
            generations.c.requested_template_id,
            generations.c.resolved_template_id,
            generations.c.requested_preset_id,
            generations.c.resolved_preset_id,
            generations.c.section_count,
            generations.c.quality_passed,
            generations.c.generation_time_seconds,
            generations.c.chunked_state_json,
            generations.c.created_at,
            generations.c.completed_at,
            generations.c.last_heartbeat,
        ).where(generations.c.id == generation_id)
    )
    generation_row = generation_result.mappings().one_or_none()
    if generation_row is None:
        raise ValueError(f"Generation not found: {generation_id}")

    step_result = await connection.execute(
        select(
            generation_steps.c.id,
            generation_steps.c.part_id,
            generation_steps.c.variant_id,
            generation_steps.c.step,
            generation_steps.c.kind,
            generation_steps.c.payload,
            generation_steps.c.created_at,
        )
        .where(generation_steps.c.generation_id == generation_id)
        .order_by(generation_steps.c.created_at, generation_steps.c.id)
    )
    call_result = await connection.execute(
        select(
            llm_calls.c.id,
            llm_calls.c.trace_id,
            llm_calls.c.caller,
            llm_calls.c.node,
            llm_calls.c.slot,
            llm_calls.c.family,
            llm_calls.c.model_name,
            llm_calls.c.endpoint_host,
            llm_calls.c.section_id,
            llm_calls.c.attempt,
            llm_calls.c.status,
            llm_calls.c.retryable,
            llm_calls.c.latency_ms,
            llm_calls.c.tokens_in,
            llm_calls.c.tokens_out,
            llm_calls.c.thinking_tokens,
            llm_calls.c.cost_usd,
            llm_calls.c.started_at,
            llm_calls.c.completed_at,
            llm_calls.c.created_at,
        )
        .where(llm_calls.c.generation_id == generation_id)
        .order_by(llm_calls.c.created_at, llm_calls.c.id)
    )

    chunked_state = generation_row["chunked_state_json"]
    generation_data = _mapping(
        generation_row,
        (
            "id",
            "subject",
            "mode",
            "status",
            "error_type",
            "error_code",
            "requested_template_id",
            "resolved_template_id",
            "requested_preset_id",
            "resolved_preset_id",
            "section_count",
            "quality_passed",
            "generation_time_seconds",
            "created_at",
            "completed_at",
            "last_heartbeat",
        ),
    )
    generation_data["stage"] = _stage(chunked_state)
    generation_data["selection_trace"] = _selection_trace(chunked_state)

    steps = []
    for row in step_result.mappings():
        item = _mapping(row, ("id", "part_id", "variant_id", "step", "kind", "created_at"))
        item["metadata"] = _step_metadata(row["payload"])
        steps.append(item)

    calls = []
    for row in call_result.mappings():
        item = _mapping(
            row,
            (
                "id",
                "trace_id",
                "caller",
                "node",
                "slot",
                "family",
                "model_name",
                "section_id",
                "attempt",
                "status",
                "retryable",
                "latency_ms",
                "tokens_in",
                "tokens_out",
                "thinking_tokens",
                "cost_usd",
                "started_at",
                "completed_at",
                "created_at",
            ),
        )
        item["endpoint_host"] = _endpoint_host(row["endpoint_host"])
        calls.append(item)

    return {
        "schema_version": SCHEMA_VERSION,
        "campaign_run_id": campaign_run_id,
        "generation_id": generation_id,
        "environment": environment,
        "commit_sha": commit_sha,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "generation": generation_data,
        "generation_steps": steps,
        "llm_calls": calls,
    }


def render_markdown(evidence: Mapping[str, Any]) -> str:
    """Render a compact reconciliation summary without content-bearing fields."""
    generation = evidence["generation"]
    steps = evidence["generation_steps"]
    calls = evidence["llm_calls"]
    step_counts = Counter(item["step"] for item in steps)
    call_counts = Counter(item["status"] for item in calls)
    latencies = [item["latency_ms"] for item in calls if item["latency_ms"] is not None]
    total_cost = sum(item["cost_usd"] or 0 for item in calls)

    def cell(value: Any) -> str:
        if value is None:
            return "—"
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        f"# Campaign run {cell(evidence['campaign_run_id'])}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generation | `{cell(evidence['generation_id'])}` |",
        f"| Environment | {cell(evidence['environment'])} |",
        f"| Commit | `{cell(evidence['commit_sha'])}` |",
        f"| Status / stage | {cell(generation['status'])} / {cell(generation['stage'])} |",
        f"| Quality passed | {cell(generation['quality_passed'])} |",
        f"| Generation seconds | {cell(generation['generation_time_seconds'])} |",
        f"| Captured at | {cell(evidence['captured_at'])} |",
        "",
        "## Database reconciliation",
        "",
        f"- Ordered generation steps: {len(steps)} ({cell(dict(step_counts))})",
        f"- LLM calls: {len(calls)} ({cell(dict(call_counts))})",
        f"- LLM latency range (ms): {cell(min(latencies) if latencies else None)}–{cell(max(latencies) if latencies else None)}",
        f"- Recorded LLM cost (USD): {total_cost:.6f}",
        "",
        "## Ordered steps",
        "",
        "| Time | Part | Variant | Step | Kind | Attempt | Recovery |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in steps:
        step_metadata = item["metadata"]
        recovery = step_metadata.get("recovery_action", step_metadata.get("recovery"))
        lines.append(
            "| "
            + " | ".join(
                cell(value)
                for value in (
                    item["created_at"],
                    item["part_id"],
                    item["variant_id"],
                    item["step"],
                    item["kind"],
                    step_metadata.get("attempt"),
                    recovery,
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _validate_label(value: str, *, name: str) -> str:
    if not _SAFE_LABEL.fullmatch(value):
        raise ValueError(f"{name} must contain only letters, numbers, dot, underscore, or hyphen")
    return value


def write_evidence(evidence: Mapping[str, Any], output_dir: Path) -> tuple[Path, Path]:
    run_id = _validate_label(str(evidence["campaign_run_id"]), name="campaign_run_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{run_id}.json"
    markdown_path = output_dir / f"{run_id}.md"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(evidence), encoding="utf-8")
    return json_path, markdown_path


def _configured_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url
    backend_src = REPO_ROOT / "backend" / "src"
    sys.path.insert(0, str(backend_src))
    from core.config import settings

    return settings.database_url


async def capture_campaign_evidence(
    *,
    database_url: str,
    generation_id: str,
    campaign_run_id: str,
    environment: str,
    commit_sha: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Capture one run from ``database_url`` and dispose its connection pool."""
    _validate_label(campaign_run_id, name="campaign_run_id")
    _validate_label(environment, name="environment")
    if not _SAFE_SHA.fullmatch(commit_sha):
        raise ValueError("commit_sha must be a 7- to 40-character hexadecimal Git SHA")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            evidence = await collect_campaign_evidence(
                connection,
                generation_id=generation_id,
                campaign_run_id=campaign_run_id,
                environment=environment,
                commit_sha=commit_sha.lower(),
            )
    finally:
        await engine.dispose()
    return write_evidence(evidence, output_dir)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--campaign-run-id", required=True)
    parser.add_argument("--environment", required=True, help="Evidence label, e.g. local or canary")
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        paths = asyncio.run(
            capture_campaign_evidence(
                database_url=_configured_database_url(),
                generation_id=args.generation_id,
                campaign_run_id=args.campaign_run_id,
                environment=args.environment,
                commit_sha=args.commit_sha,
                output_dir=args.output_dir,
            )
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
