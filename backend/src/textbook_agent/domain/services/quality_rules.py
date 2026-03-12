import ast
import re

from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityIssue
from textbook_agent.domain.entities.textbook import RawTextbook

_UNICODE_SUB_SUPERSCRIPTS = set("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹")
_BOLD_RUN_RE = re.compile(r"(\*\*[^*]+\*\*|<strong>.*?</strong>)\s+(\*\*[^*]+\*\*|<strong>.*?</strong>)")


def _issue(
    section_id: str,
    issue_type: str,
    description: str,
    severity: str = "error",
) -> QualityIssue:
    return QualityIssue(
        section_id=section_id,
        issue_type=issue_type,
        description=description,
        severity=severity,
        check_source="mechanical",
    )


def _body_blocks(section) -> list[tuple[str, str]]:
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


def run_mechanical_checks(
    textbook: RawTextbook,
    plan: CurriculumPlan,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    section_map = {section.section_id: section for section in textbook.sections}

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

    for diagram in textbook.diagrams:
        missing_attrs = [
            attr
            for attr in ("width", "height", "viewBox")
            if re.search(rf"\b{attr}\s*=", diagram.svg_markup) is None
        ]
        if missing_attrs:
            issues.append(
                _issue(
                    diagram.section_id,
                    "svg_missing_required_attributes",
                    f"Diagram SVG is missing required attributes: {', '.join(missing_attrs)}.",
                    severity="warning",
                )
            )

    for code_example in textbook.code_examples:
        if not code_example.language.strip():
            issues.append(
                _issue(
                    code_example.section_id,
                    "missing_code_language",
                    "Code examples must declare a language.",
                )
            )

        for line_number, line in enumerate(code_example.code.splitlines(), start=1):
            if len(line) > 300:
                issues.append(
                    _issue(
                        code_example.section_id,
                        "code_line_too_long",
                        f"Code line {line_number} exceeds the 300 character hard limit.",
                    )
                )
            elif len(line) > 80:
                issues.append(
                    _issue(
                        code_example.section_id,
                        "code_line_too_long",
                        f"Code line {line_number} exceeds the 80 character soft limit.",
                        severity="warning",
                    )
                )

        if code_example.language.strip().lower() == "python":
            try:
                ast.parse(code_example.code)
            except SyntaxError as exc:
                issues.append(
                    _issue(
                        code_example.section_id,
                        "invalid_python_code",
                        f"Python code failed to parse: {exc.msg}.",
                    )
                )

    return issues
