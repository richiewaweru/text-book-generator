from textbook_agent.domain.entities.quality_report import QualityReport


def group_retry_issues(report: QualityReport) -> dict[str, list]:
    """Group retryable issues by section id."""
    grouped: dict[str, list] = {}
    for issue in report.issues:
        if issue.severity != "error" or issue.scope != "section" or not issue.section_id:
            continue
        grouped.setdefault(issue.section_id, []).append(issue)
    return grouped


def decide_reruns(report: QualityReport) -> list[str]:
    """Extract section IDs that need re-generation from a quality report.

    Only sections with error-severity issues are flagged for rerun.
    Warning-severity issues are informational and don't trigger reruns.
    """
    return list(group_retry_issues(report))


def document_blockers(report: QualityReport) -> list:
    """Return non-retryable document-scoped errors."""
    return [
        issue
        for issue in report.issues
        if issue.severity == "error" and issue.scope == "document"
    ]
