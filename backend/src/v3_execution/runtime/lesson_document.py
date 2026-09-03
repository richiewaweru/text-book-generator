"""Assemble LessonDocument-shaped artifacts from checkpoints (Phase 08)."""

from __future__ import annotations

from typing import Any

from v3_blueprint.planning.canonical_plan import CanonicalExecutionPlan
from v3_execution.runtime.checkpoints import CheckpointStore


def assemble_lesson_document(
    plan: CanonicalExecutionPlan,
    store: CheckpointStore,
    *,
    title: str,
    human_revision: int = 0,
    generator_revision: int | None = None,
) -> dict[str, Any]:
    """Build a Builder-openable LessonDocument-shaped dict from ready checkpoints.

    Human-edit fence: if human_revision > generator_revision, ready generator
    payloads for older revisions are ignored for those blocks.
    """
    gen_rev = plan.plan_revision if generator_revision is None else generator_revision
    blocks: dict[str, Any] = {}
    sections: list[dict[str, Any]] = []

    ready = {
        block_id: checkpoint
        for block_id, checkpoint in store.blocks.items()
        if checkpoint.state == "ready"
    }

    for section in plan.sections:
        block_ids: list[str] = []
        for block_id in section.block_ids:
            checkpoint = ready.get(block_id)
            if checkpoint is None:
                continue
            if human_revision > gen_rev and checkpoint.plan_revision <= gen_rev:
                # Stale generator loses to newer human edit fence.
                continue
            meta = next(b for b in plan.blocks if b.block_id == block_id)
            blocks[block_id] = {
                "id": block_id,
                "component_id": meta.component_id,
                "content": checkpoint.payload.get("content", {}),
                "position": meta.position,
            }
            block_ids.append(block_id)
        sections.append(
            {
                "id": section.section_id,
                "title": section.title,
                "role": section.role,
                "block_ids": block_ids,
            }
        )

    return {
        "schema": "LessonDocument",
        "title": title,
        "plan_hash": plan.plan_hash,
        "plan_revision": plan.plan_revision,
        "human_revision": human_revision,
        "sections": sections,
        "blocks": blocks,
        "partial": any(
            block_id not in blocks
            for section in plan.sections
            for block_id in section.block_ids
        ),
    }


def reconnect_from_store(store: CheckpointStore) -> dict[str, Any]:
    """Browser/SSE reconnect reconstructs from durable store alone."""
    return store.reconstruct()
