import asyncio

from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.quality_report import QualityIssue, QualityReport
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.prompts.inline_quality_prompts import (
    build_inline_quality_prompt,
)

from .quality_rules import run_section_mechanical_checks
from .severity_policy import apply_severity_policy


class InlineQualityChecker:
    """Runs fast per-section quality review during generation."""

    def __init__(
        self,
        provider: BaseProvider,
        *,
        code_line_soft_limit: int = 80,
        code_line_hard_limit: int = 300,
        model_override: str | None = None,
    ) -> None:
        self.provider = provider
        self.code_line_soft_limit = code_line_soft_limit
        self.code_line_hard_limit = code_line_hard_limit
        self.model_override = model_override

    async def check_section(
        self,
        section: SectionSpec,
        content: SectionContent,
        diagram: SectionDiagram | None = None,
        code_example: SectionCode | None = None,
    ) -> QualityReport:
        mechanical_issues = run_section_mechanical_checks(
            content,
            diagram=diagram,
            code_example=code_example,
            code_line_soft_limit=self.code_line_soft_limit,
            code_line_hard_limit=self.code_line_hard_limit,
        )
        prompt = build_inline_quality_prompt(
            section,
            content,
            diagram=diagram,
            code_example=code_example,
        )
        llm_report = await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Review section: {section.title}",
            response_schema=QualityReport,
            model=self.model_override,
        )
        llm_issues = [
            _normalize_inline_issue(issue, section.id) for issue in llm_report.issues
        ]
        llm_issues = apply_severity_policy(llm_issues)
        merged_issues = [*mechanical_issues, *llm_issues]
        return QualityReport(
            passed=not any(issue.severity == "error" for issue in merged_issues),
            issues=merged_issues,
        )


def _normalize_inline_issue(issue: QualityIssue, section_id: str) -> QualityIssue:
    return issue.model_copy(
        update={
            "section_id": issue.section_id or section_id,
            "scope": "section",
            "check_source": "llm",
        }
    )
