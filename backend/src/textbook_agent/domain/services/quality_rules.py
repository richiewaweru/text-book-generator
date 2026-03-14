import ast
import re

from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityIssue
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.textbook import RawTextbook

_UNICODE_SUB_SUPERSCRIPTS = set("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")
_BOLD_RUN_RE = re.compile(
    r"(\*\*[^*]+\*\*|<strong>.*?</strong>)\s+(\*\*[^*]+\*\*|<strong>.*?</strong>)"
)


def _issue(
    section_id: str | None,
    issue_type: str,
    description: str,
    *,
    severity: str = "error",
    scope: str = "section",
) -> QualityIssue:
    return QualityIssue(
        section_id=section_id,
        issue_type=issue_type,
        description=description,
        severity=severity,
        scope=scope,
        check_source="mechanical",
    )


def _body_blocks(section: SectionContent) -> list[tuple[str, str]]:
    return [
        ("hook", section.hook),
        ("prerequisites_block", section.prerequisites_block),
        ("plain_explanation", section.plain_explanation),
        ("formal_definition", section.formal_definition),
        ("worked_example", section.worked_example),
        ("common_misconception", section.common_misconception),
        ("interview_anchor", section.interview_anchor),
        ("think_prompt", section.think_prompt),
        ("connection_forward", section.connection_forward),
    ]


def check_section_content(section: SectionContent) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    section_id = section.section_id

    if not section.hook.strip():
        issues.append(
            _issue(
                section_id,
                "missing_hook",
                "Each section must begin with a non-empty intuition hook.",
            )
        )

    if len(section.practice_problems) != 3:
        issues.append(
            _issue(
                section_id,
                "invalid_practice_problem_count",
                "Each section must include exactly three practice problems.",
            )
        )
    else:
        difficulties = [problem.difficulty for problem in section.practice_problems]
        if sorted(difficulties) != ["cold", "medium", "warm"]:
            issues.append(
                _issue(
                    section_id,
                    "invalid_practice_problem_difficulties",
                    "Practice problems must include one warm, one medium, and one cold item.",
                )
            )

    for problem in section.practice_problems:
        if not problem.statement.strip():
            issues.append(
                _issue(
                    section_id,
                    "empty_practice_problem_statement",
                    "Practice problem statements must not be empty.",
                )
            )
        if not problem.hint.strip():
            issues.append(
                _issue(
                    section_id,
                    "empty_practice_problem_hint",
                    "Practice problem hints must not be empty.",
                )
            )

    for field_name, text in _body_blocks(section):
        if not text:
            continue
        if "!" in text:
            issues.append(
                _issue(
                    section_id,
                    "exclamation_mark_in_body",
                    f"The {field_name} field contains an exclamation mark.",
                    severity="warning",
                )
            )
        if any(char in _UNICODE_SUB_SUPERSCRIPTS for char in text):
            issues.append(
                _issue(
                    section_id,
                    "unicode_subscript_or_superscript",
                    f"The {field_name} field uses Unicode subscript or superscript characters.",
                )
            )
        if _BOLD_RUN_RE.search(text):
            issues.append(
                _issue(
                    section_id,
                    "consecutive_bold_runs",
                    f"The {field_name} field uses consecutive bold runs.",
                    severity="warning",
                )
            )

    return issues


def check_diagram(diagram: SectionDiagram | None) -> list[QualityIssue]:
    if diagram is None:
        return []

    missing_attrs = [
        attr
        for attr in ("width", "height", "viewBox")
        if re.search(rf"\b{attr}\s*=", diagram.svg_markup) is None
    ]
    if not missing_attrs:
        return []

    return [
        _issue(
            diagram.section_id,
            "svg_missing_required_attributes",
            f"Diagram SVG is missing required attributes: {', '.join(missing_attrs)}.",
            severity="warning",
        )
    ]


def check_code(
    code_example: SectionCode | None,
    *,
    code_line_soft_limit: int = 80,
    code_line_hard_limit: int = 300,
) -> list[QualityIssue]:
    if code_example is None:
        return []

    issues: list[QualityIssue] = []
    section_id = code_example.section_id

    if not code_example.language.strip():
        issues.append(
            _issue(
                section_id,
                "missing_code_language",
                "Code examples must declare a language.",
            )
        )

    for line_number, line in enumerate(code_example.code.splitlines(), start=1):
        if len(line) > code_line_hard_limit:
            issues.append(
                _issue(
                    section_id,
                    "code_line_too_long",
                    f"Code line {line_number} exceeds the {code_line_hard_limit} character hard limit.",
                )
            )
        elif len(line) > code_line_soft_limit:
            issues.append(
                _issue(
                    section_id,
                    "code_line_too_long",
                    f"Code line {line_number} exceeds the {code_line_soft_limit} character soft limit.",
                    severity="warning",
                )
            )

    if code_example.language.strip().lower() == "python":
        try:
            ast.parse(code_example.code)
        except SyntaxError as exc:
            issues.append(
                _issue(
                    section_id,
                    "invalid_python_code",
                    f"Python code failed to parse: {exc.msg}.",
                )
            )

    return issues


def run_section_mechanical_checks(
    section: SectionContent,
    *,
    diagram: SectionDiagram | None = None,
    code_example: SectionCode | None = None,
    code_line_soft_limit: int = 80,
    code_line_hard_limit: int = 300,
) -> list[QualityIssue]:
    issues = check_section_content(section)
    issues.extend(check_diagram(diagram))
    issues.extend(
        check_code(
            code_example,
            code_line_soft_limit=code_line_soft_limit,
            code_line_hard_limit=code_line_hard_limit,
        )
    )
    return issues


def run_mechanical_checks(
    textbook: RawTextbook,
    plan: CurriculumPlan,
    *,
    code_line_soft_limit: int = 80,
    code_line_hard_limit: int = 300,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    section_map = {section.section_id: section for section in textbook.sections}
    diagram_map = {diagram.section_id: diagram for diagram in textbook.diagrams}
    code_map = {
        code_example.section_id: code_example for code_example in textbook.code_examples
    }

    for section_id in plan.reading_order:
        section = section_map.get(section_id)
        if section is None:
            issues.append(
                _issue(
                    section_id,
                    "missing_section_content",
                    "The curriculum plan includes this section but the textbook does not.",
                )
            )
            continue

        issues.extend(
            run_section_mechanical_checks(
                section,
                diagram=diagram_map.get(section_id),
                code_example=code_map.get(section_id),
                code_line_soft_limit=code_line_soft_limit,
                code_line_hard_limit=code_line_hard_limit,
            )
        )

    return issues
