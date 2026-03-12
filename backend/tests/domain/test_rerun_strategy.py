from textbook_agent.domain.entities.quality_report import (
    QualityIssue,
    QualityReport,
)
from textbook_agent.domain.services.rerun_strategy import decide_reruns


class TestDecideReruns:
    def test_returns_only_error_sections(self):
        report = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_01",
                    issue_type="missing_prerequisite",
                    description="References integration before defined",
                    severity="error",
                ),
                QualityIssue(
                    section_id="section_02",
                    issue_type="terminology_inconsistency",
                    description="Uses 'function' and 'map' interchangeably",
                    severity="warning",
                ),
            ],
        )
        result = decide_reruns(report)
        assert result == ["section_01"]

    def test_deduplicates_sections(self):
        report = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_03",
                    issue_type="missing_prerequisite",
                    description="Issue A",
                    severity="error",
                ),
                QualityIssue(
                    section_id="section_03",
                    issue_type="complexity_spike",
                    description="Issue B",
                    severity="error",
                ),
            ],
        )
        result = decide_reruns(report)
        assert result == ["section_03"]

    def test_passing_report_returns_empty(self):
        report = QualityReport(passed=True, issues=[])
        assert decide_reruns(report) == []

    def test_warnings_only_returns_empty(self):
        report = QualityReport(
            passed=False,
            issues=[
                QualityIssue(
                    section_id="section_01",
                    issue_type="minor_style",
                    description="Minor issue",
                    severity="warning",
                ),
            ],
        )
        assert decide_reruns(report) == []
