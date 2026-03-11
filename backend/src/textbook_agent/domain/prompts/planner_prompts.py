from textbook_agent.domain.entities.learner_profile import LearnerProfile
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_planner_prompt(profile: LearnerProfile) -> str:
    """Build the system prompt for the Curriculum Planner node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

You are planning the curriculum for a personalized {profile.subject} textbook.

LEARNER:
- Age: {profile.age}
- Depth requested: {profile.depth.value}
- Context: {profile.context}

Your task: produce a CurriculumPlan.

Requirements:
- Order topics so that no section requires knowledge not covered in a prior section.
- For STEM subjects, prerequisite ordering is critical — enforce it strictly.
- Mark sections as core or supplementary based on depth requested.
- Identify which sections need a diagram and which need a code example.
- For "survey" depth: include only core sections.
- For "standard" depth: include core + key supplementary sections.
- For "deep" depth: include everything.

Return your response as a valid JSON object conforming to the CurriculumPlan schema.
"""
