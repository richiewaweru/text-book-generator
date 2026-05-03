from __future__ import annotations

from typing import Any

from v3_review.models import CoherenceReport


def coherence_report_to_generation_summary(report: CoherenceReport) -> dict[str, Any]:
    """Serialize coherence review for GenerationReport.coherence_review (forward-compatible)."""
    return {
        "blueprint_id": report.blueprint_id,
        "generation_id": report.generation_id,
        "status": report.status,
        "deterministic_passed": report.deterministic_passed,
        "llm_review_passed": report.llm_review_passed,
        "blocking_count": report.blocking_count,
        "major_count": report.major_count,
        "minor_count": report.minor_count,
        "repair_target_count": len(report.repair_targets),
        "repaired_target_count": len(report.repaired_target_ids),
        "repair_attempts": dict(report.repair_attempts),
        "issue_categories": _category_histogram(report),
    }


def _category_histogram(report: CoherenceReport) -> dict[str, int]:
    hist: dict[str, int] = {}
    for issue in report.issues:
        hist[issue.category] = hist.get(issue.category, 0) + 1
    return hist


__all__ = ["coherence_report_to_generation_summary"]
