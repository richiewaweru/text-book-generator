from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_quality_prompt(textbook: RawTextbook, plan: CurriculumPlan) -> str:
    """Build the system prompt for the Quality Checker node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

You are reviewing a generated textbook for correctness, coherence, and
pedagogical quality.

TEXTBOOK:
- Subject: {textbook.subject}
- Sections generated: {len(textbook.sections)}
- Diagrams generated: {len(textbook.diagrams)}
- Code examples generated: {len(textbook.code_examples)}

PLAN:
- Subject: {plan.subject}
- Total planned sections: {plan.total_sections}
- Reading order: {", ".join(plan.reading_order)}

Return only valid JSON matching the QualityReport schema.
Flag issues that would cause learner confusion, logical gaps, or violations of
the curriculum order.
"""
