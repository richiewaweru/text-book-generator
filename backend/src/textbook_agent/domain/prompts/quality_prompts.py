from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.textbook import RawTextbook

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_quality_prompt(textbook: RawTextbook, plan: CurriculumPlan) -> str:
    """Build the system prompt for the Quality Checker node."""
    return compose_prompt(
        "quality_checker",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are reviewing a fully assembled textbook for cross-section correctness,
coherence, and pedagogical quality.

TEXTBOOK:
- Subject: {textbook.subject}
- Sections generated: {len(textbook.sections)}
- Diagrams generated: {len(textbook.diagrams)}
- Code examples generated: {len(textbook.code_examples)}

PLAN:
- Subject: {plan.subject}
- Total planned sections: {plan.total_sections}
- Reading order: {", ".join(plan.reading_order)}

Focus on document-level and cross-section issues only:
- structure completeness across the assembled textbook
- forward references to concepts introduced later
- terminology drift across sections
- symbols redefined with different meanings
- difficulty spikes across neighboring sections
- section ordering or progression problems
- section-specific semantic issues that became visible only in document context

DO NOT CHECK the following - they are already verified by automated mechanical checks:
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

Scope rules:
- Use scope "section" when an issue can be fixed by repairing one section.
- Use scope "document" when the issue spans the textbook and cannot be safely
  repaired by rerunning one section alone.
- Section-scoped issues must include a section_id.
- Document-scoped issues must set section_id to null.

Return only valid JSON matching the QualityReport schema.
Flag only issues that would cause learner confusion, logical gaps, or
violations of the curriculum order.
""",
    )
