from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from v3_review.models import RepairExecutor, RepairTarget, ReviewIssue

TargetKind = Literal["section_component", "question", "visual", "answer_key", "assembly"]


def _executor_to_target_type(executor: RepairExecutor) -> TargetKind:
    mapping: dict[RepairExecutor, TargetKind] = {
        "section_writer": "section_component",
        "question_writer": "question",
        "visual_executor": "visual",
        "answer_key_generator": "answer_key",
        "assembler": "assembly",
    }
    return mapping[executor]


def build_repair_targets(issues: Sequence[ReviewIssue]) -> list[RepairTarget]:
    """Emit actionable repair targets for blocking and major issues (deduped)."""
    actionable = [i for i in issues if i.severity in ("blocking", "major")]
    seen: set[str] = set()
    targets: list[RepairTarget] = []

    for issue in actionable:
        ex = issue.suggested_repair_executor
        tid = issue.repair_target_id or _fallback_target_id(issue)
        if tid in seen:
            continue
        seen.add(tid)

        sec_id, comp_id, qid, vid = _parse_ids_from_issue(issue)

        targets.append(
            RepairTarget(
                target_id=tid,
                executor=ex,
                source_work_order_id=None,
                target_type=_executor_to_target_type(ex),
                target_ref=_human_ref(issue, tid),
                section_id=sec_id,
                component_id=comp_id,
                question_id=qid,
                visual_id=vid,
                reason=issue.message,
                constraints=[],
                severity=issue.severity,
            )
        )

    return targets


def _fallback_target_id(issue: ReviewIssue) -> str:
    cat = issue.category
    ref = issue.generated_ref or issue.blueprint_ref or issue.issue_id
    return f"{cat}:{ref}"


def _human_ref(issue: ReviewIssue, tid: str) -> str:
    parts = [tid]
    if issue.generated_ref:
        parts.append(issue.generated_ref)
    return " · ".join(parts)


def _parse_ids_from_issue(issue: ReviewIssue) -> tuple[str | None, str | None, str | None, str | None]:
    rid = issue.repair_target_id or ""
    sec_id = None
    comp_id = None
    qid = None
    vid = None
    if rid.startswith("section:"):
        sec_id = rid.split(":", 1)[1]
    elif rid.startswith("component:"):
        bits = rid.split(":")
        if len(bits) >= 3:
            sec_id = bits[1]
            comp_id = bits[2]
    elif rid.startswith("questions:"):
        sec_id = rid.split(":", 1)[1]
    elif rid.startswith("visual:"):
        rest = rid.split(":", 1)[1]
        sec_id = rest
        vid = None
    elif rid.startswith("answer_key:"):
        tail = rid.split(":", 1)[1]
        if tail != "main":
            qid = tail
    elif rid.startswith("schema:"):
        sec_id = rid.split(":", 1)[1]
    return sec_id, comp_id, qid, vid


__all__ = ["build_repair_targets"]
