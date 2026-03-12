"""Severity policy for LLM-returned quality issues.

Maps issue_type to the maximum allowed severity. If the LLM returns a
higher severity than the policy allows, the issue is downgraded.
This prevents cosmetic or stylistic issues from blocking delivery
and burning rerun budget.
"""

from textbook_agent.domain.entities.quality_report import QualityIssue

# Issue types that the LLM may return but should never exceed "warning".
# Any issue_type NOT in this set keeps whatever severity the LLM assigned.
_WARNING_ONLY_ISSUE_TYPES: set[str] = {
    # Formatting / style — not learning failures
    "bold_overuse",
    "excessive_bold",
    "multiple_bold",
    "exclamation_mark",
    "exclamation_in_prose",
    "nested_callout",
    "nested_callouts",
    "empty_definition_box",
    "empty_definition",
    "adjacent_headings",
    "heading_hierarchy",
    # Table / layout — renderer concerns
    "table_too_tall",
    "table_height",
    "table_overflow",
    # Code style — not broken, just messy
    "commented_out_code",
    "commented_code",
    "code_line_too_long",
    # Colour — enforced by CSS, not LLM content
    "colour_consistency",
    "color_consistency",
    "semantic_colour",
    "semantic_color",
    "forbidden_colour",
    "forbidden_color",
    "colour_combination",
    "color_combination",
    # Numbering — renderer could auto-number
    "worked_example_numbering",
    "example_numbering",
    # Duplicates of mechanical checks — LLM shouldn't escalate
    "missing_code_language",
    "code_language_missing",
    "svg_missing_attributes",
    "svg_missing_required_attributes",
}


def apply_severity_policy(issues: list[QualityIssue]) -> list[QualityIssue]:
    """Downgrade LLM issues that match Tier 2 (warning-only) policy."""
    result: list[QualityIssue] = []
    for issue in issues:
        if (
            issue.severity == "error"
            and issue.issue_type in _WARNING_ONLY_ISSUE_TYPES
        ):
            result.append(issue.model_copy(update={"severity": "warning"}))
        else:
            result.append(issue)
    return result
