from textbook_agent.domain.entities.quality_report import QualityReport


def decide_reruns(report: QualityReport) -> list[str]:
    """Extract section IDs that need re-generation from a quality report.

    Only sections with error-severity issues are flagged for rerun.
    Warning-severity issues are informational and don't trigger reruns.
    """
    section_ids: list[str] = []
    seen: set[str] = set()
    for issue in report.issues:
        if issue.severity == "error" and issue.section_id not in seen:
            section_ids.append(issue.section_id)
            seen.add(issue.section_id)
    return section_ids
