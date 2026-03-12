from textbook_agent.domain.entities.practice_problem import PracticeProblem
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.services.quality_rules import run_mechanical_checks


def test_run_mechanical_checks_accepts_valid_sample(beginner_profile, sample_plan, sample_content):
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=sample_plan,
        sections=[sample_content],
        diagrams=[
            SectionDiagram(
                section_id="section_01",
                svg_markup='<svg width="100" height="40" viewBox="0 0 100 40"></svg>',
                caption="Valid sample",
                diagram_type="number_line",
            )
        ],
        code_examples=[
            SectionCode(
                section_id="section_01",
                language="python",
                code="x = 4\nprint(x)",
                explanation="Shows the variable value.",
                expected_output="4",
            )
        ],
    )

    issues = run_mechanical_checks(textbook=textbook, plan=sample_plan)

    assert issues == []


def test_run_mechanical_checks_flags_missing_section(beginner_profile, sample_plan):
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=sample_plan,
        sections=[],
    )

    issues = run_mechanical_checks(textbook=textbook, plan=sample_plan)

    assert any(issue.issue_type == "missing_section_content" for issue in issues)


def test_run_mechanical_checks_flags_invalid_practice_problem_structure(
    beginner_profile,
    sample_plan,
):
    section = SectionContent(
        section_id="section_01",
        hook="Hook",
        plain_explanation="Explanation",
        formal_definition="Definition",
        worked_example="Worked example",
        common_misconception="Misconception",
        practice_problems=[
            PracticeProblem(
                difficulty="warm",
                statement="One",
                hint="Hint one",
            ),
            PracticeProblem(
                difficulty="warm",
                statement="Two",
                hint="Hint two",
            ),
        ],
        connection_forward="Next section",
    )
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=sample_plan,
        sections=[section],
    )

    issues = run_mechanical_checks(textbook=textbook, plan=sample_plan)

    assert any(issue.issue_type == "invalid_practice_problem_count" for issue in issues)


def test_run_mechanical_checks_flags_svg_and_code_violations(
    beginner_profile,
    sample_plan,
    sample_content,
):
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=sample_plan,
        sections=[sample_content],
        diagrams=[
            SectionDiagram(
                section_id="section_01",
                svg_markup="<svg height='40'></svg>",
                caption="Broken sample",
                diagram_type="number_line",
            )
        ],
        code_examples=[
            SectionCode(
                section_id="section_01",
                language="python",
                code="if True print('broken')" + ("x" * 81),
                explanation="Broken code sample",
                expected_output="",
            )
        ],
    )

    issues = run_mechanical_checks(textbook=textbook, plan=sample_plan)

    assert any(issue.issue_type == "svg_missing_required_attributes" for issue in issues)
    assert any(issue.issue_type == "code_line_too_long" for issue in issues)
    assert any(issue.issue_type == "invalid_python_code" for issue in issues)


def test_run_mechanical_checks_flags_forbidden_formatting(beginner_profile, sample_plan):
    section = SectionContent(
        section_id="section_01",
        hook="Hook!",
        plain_explanation="Use x₁ and **this** **that** together.",
        formal_definition="Definition",
        worked_example="Worked example",
        common_misconception="Misconception",
        practice_problems=[
            PracticeProblem(
                difficulty="warm",
                statement="One",
                hint="Hint one",
            ),
            PracticeProblem(
                difficulty="medium",
                statement="Two",
                hint="Hint two",
            ),
            PracticeProblem(
                difficulty="cold",
                statement="Three",
                hint="Hint three",
            ),
        ],
        connection_forward="Next section",
    )
    textbook = RawTextbook(
        subject="algebra",
        profile=beginner_profile,
        plan=sample_plan,
        sections=[section],
    )

    issues = run_mechanical_checks(textbook=textbook, plan=sample_plan)

    assert any(issue.issue_type == "exclamation_mark_in_body" for issue in issues)
    assert any(issue.issue_type == "unicode_subscript_or_superscript" for issue in issues)
    assert any(issue.issue_type == "consecutive_bold_runs" for issue in issues)
