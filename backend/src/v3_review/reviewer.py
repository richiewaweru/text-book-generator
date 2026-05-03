from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from v3_blueprint.models import ProductionBlueprint
from v3_execution.models import DraftPack
from v3_execution.runtime import events as v3_events

from v3_review.deterministic_checks import (
    check_anchor_facts,
    check_answer_key_entries,
    check_component_ids_in_manifest,
    check_expected_answers_preserved,
    check_internal_artifact_leaks,
    check_lectio_schema_validity,
    check_no_extra_questions,
    check_no_extra_sections,
    check_planned_components_exist,
    check_planned_questions_exist,
    check_planned_sections_exist,
    check_planned_visuals_exist,
    check_visuals_attach_to_valid_targets,
)
from v3_review.llm_review import run_llm_review
from v3_review.models import CoherenceReport, ReviewIssue, derive_coherence_status, refresh_issue_counts
from v3_review.targets import build_repair_targets

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_coherence_review(
    blueprint: ProductionBlueprint,
    draft_pack: DraftPack,
    manifest: dict[str, Any],
    emit_event: EmitFn,
    *,
    trace_id: str | None = None,
    generation_id: str | None = None,
    model_overrides: dict | None = None,
) -> CoherenceReport:
    gid = generation_id or draft_pack.generation_id

    await emit_event(v3_events.COHERENCE_REVIEW_STARTED, {"generation_id": gid})

    await emit_event(v3_events.DETERMINISTIC_REVIEW_STARTED, {"generation_id": gid})

    det_issues: list[ReviewIssue] = []
    det_issues += check_planned_sections_exist(blueprint, draft_pack)
    det_issues += check_no_extra_sections(blueprint, draft_pack)
    det_issues += check_planned_components_exist(blueprint, draft_pack)
    det_issues += check_planned_questions_exist(blueprint, draft_pack)
    det_issues += check_no_extra_questions(blueprint, draft_pack)
    det_issues += check_planned_visuals_exist(blueprint, draft_pack)
    det_issues += check_visuals_attach_to_valid_targets(blueprint, draft_pack)
    det_issues += check_answer_key_entries(blueprint, draft_pack)
    det_issues += check_expected_answers_preserved(blueprint, draft_pack)
    det_issues += check_anchor_facts(blueprint, draft_pack)
    det_issues += check_internal_artifact_leaks(draft_pack)
    det_issues += check_lectio_schema_validity(draft_pack, manifest)
    det_issues += check_component_ids_in_manifest(blueprint, draft_pack, manifest)

    await emit_event(
        v3_events.DETERMINISTIC_REVIEW_COMPLETE,
        {
            "generation_id": gid,
            "issue_count": len(det_issues),
            "blocking": sum(1 for i in det_issues if i.severity == "blocking"),
        },
    )

    det_blocking = [i for i in det_issues if i.severity == "blocking"]
    schema_failures = [i for i in det_issues if i.category == "schema_violation"]
    missing_sections = [
        i
        for i in det_issues
        if i.category == "missing_planned_content" and "section" in i.message.lower()
    ]

    skip_llm = (
        len(det_blocking) > 5 or len(schema_failures) > 2 or len(missing_sections) > 1
    )

    if skip_llm:
        await emit_event(
            v3_events.LLM_REVIEW_SKIPPED,
            {
                "generation_id": gid,
                "reason": "Deterministic failures too severe — repair first",
            },
        )
        llm_issues: list[ReviewIssue] = []
    else:
        await emit_event(v3_events.LLM_REVIEW_STARTED, {"generation_id": gid})
        llm_issues = await run_llm_review(
            blueprint,
            draft_pack,
            det_issues,
            trace_id=trace_id,
            generation_id=gid,
            model_overrides=model_overrides,
        )
        await emit_event(
            v3_events.LLM_REVIEW_COMPLETE,
            {"generation_id": gid, "issue_count": len(llm_issues)},
        )

    all_issues = det_issues + llm_issues
    repair_targets = build_repair_targets(all_issues)

    status = derive_coherence_status(all_issues, repair_targets)

    report = CoherenceReport(
        blueprint_id=draft_pack.blueprint_id,
        generation_id=draft_pack.generation_id,
        status=status,
        deterministic_passed=not any(i.severity == "blocking" for i in det_issues),
        llm_review_passed=not any(i.severity == "blocking" for i in llm_issues),
        issues=all_issues,
        repair_targets=repair_targets,
    )
    refresh_issue_counts(report)

    await emit_event(
        v3_events.COHERENCE_REPORT_READY,
        {
            "generation_id": gid,
            "status": status,
            "blocking_count": report.blocking_count,
            "repair_target_count": len(repair_targets),
        },
    )

    return report


__all__ = ["run_coherence_review"]
