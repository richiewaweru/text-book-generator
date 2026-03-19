"""
Shared context and utilities used across all prompt builders.
The shared context block is small -- 3 lines max.
It appears in every system prompt.
"""

from __future__ import annotations


def shared_context(
    template_name: str,
    template_family: str,
    subject: str,
    grade_band: str,
    learner_fit: str,
) -> str:
    """
    A small anchor block included in every system prompt.
    Keeps every node aware of the teaching context
    without duplicating the full contract into every call.
    """
    return f"""Template: {template_name} ({template_family} family)
Subject: {subject}
Learner: {grade_band} level, {learner_fit}"""


def word_count(text: str) -> int:
    return len(text.strip().split())


def capacity_reminder() -> str:
    """
    Inline capacity rules for the content generator system prompt.
    These mirror src/lib/validate.ts exactly.
    """
    return """Capacity rules (hard limits -- do not exceed):
- hook.headline: 12 words max
- hook.body: 80 words max
- explanation.body: 350 words max
- explanation.emphasis: 3 items max
- practice.problems: 2 min, 5 max
- practice hints per problem: 3 max
- glossary.terms: 8 max
- worked_example.steps: 6 max
- what_next.body: 50 words max
- definition.formal: 80 words max
- definition.plain: 60 words max"""
