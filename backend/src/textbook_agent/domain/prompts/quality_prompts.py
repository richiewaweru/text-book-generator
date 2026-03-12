from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.textbook import RawTextbook

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_quality_prompt(textbook: RawTextbook, plan: CurriculumPlan) -> str:
    """Build the system prompt for the Quality Checker node."""
    return compose_prompt(
        "quality_checker",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are reviewing a generated textbook for correctness, coherence, formatting compliance,
and pedagogical quality.

TEXTBOOK:
- Subject: {textbook.subject}
- Sections generated: {len(textbook.sections)}
- Diagrams generated: {len(textbook.diagrams)}
- Code examples generated: {len(textbook.code_examples)}

PLAN:
- Subject: {plan.subject}
- Total planned sections: {plan.total_sections}
- Reading order: {", ".join(plan.reading_order)}

Check categories:
- structure completeness
- terminology consistency
- difficulty progression
- worked-example alignment
- formatting and notation compliance
- diagram and code quality

DO NOT CHECK the following — they are already verified by automated mechanical checks:
- Practice problem count or difficulty distribution
- Empty practice problem statements or hints
- Missing hooks (empty hook field)
- Missing section content
- Unicode subscript/superscript characters
- Consecutive bold runs
- Exclamation marks in body prose
- SVG width/height/viewBox attributes
- Code language declaration
- Code line length
- Python syntax validity (ast.parse)

Focus your review on semantic and pedagogical quality that code cannot verify:
forward references, symbol consistency, difficulty progression, tone, and
structural coherence.

Return only valid JSON matching the QualityReport schema.
Flag issues that would cause learner confusion, logical gaps, or violations of the curriculum order.
""",
    )
