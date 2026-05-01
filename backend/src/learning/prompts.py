from __future__ import annotations


PACK_LEARNING_PLAN_SYSTEM = """
You create the shared instructional anchor for a learning pack.
Return only valid JSON matching the PackLearningPlan schema.

Rules:
- objective: one measurable sentence
- success_criteria: at most 3 observable items
- prerequisite_skills: at most 3 items
- likely_misconceptions: at most 2 items
- shared_vocabulary: 3 to 6 consistent terms
- shared_examples: 1 to 2 concrete anchor examples

Every generated resource in the pack will receive this plan, so make it specific,
coherent, and grounded in the learning job.
""".strip()


def build_pack_learning_plan_user_prompt(
    *,
    job_type: str,
    subject: str,
    topic: str,
    grade_level: str,
    objective_hint: str,
    class_signals: list[str],
    warnings: list[str],
    pack_intent: str,
) -> str:
    return "\n".join(
        [
            f"Pack type: {job_type}",
            f"Subject: {subject}",
            f"Topic: {topic}",
            f"Grade level: {grade_level}",
            f"Objective hint: {objective_hint}",
            f"Class signals: {', '.join(class_signals) or 'none'}",
            f"Warnings: {', '.join(warnings) or 'none'}",
            "",
            "Pack intent:",
            pack_intent.strip(),
        ]
    )
