from textbook_agent.domain.entities.learner_profile import LearnerProfile
from .base_prompt import BASE_PEDAGOGICAL_RULES


def _learner_block(profile: LearnerProfile) -> str:
    """Build the LEARNER context block shared across prompts."""
    lines = [
        f"- Age: {profile.age}",
        f"- Education level: {profile.education_level.value}",
        f"- Depth requested: {profile.depth.value}",
        f"- Learning style: {profile.learning_style.value}",
        f"- Context: {profile.context}",
    ]
    if profile.interests:
        lines.append(f"- Interests: {', '.join(profile.interests)}")
    if profile.goals:
        lines.append(f"- Goals: {profile.goals}")
    return "\n".join(lines)


def build_planner_prompt(profile: LearnerProfile) -> str:
    """Build the system prompt for the Curriculum Planner node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

You are planning the curriculum for a personalized {profile.subject} textbook.

LEARNER:
{_learner_block(profile)}

Your task: produce a CurriculumPlan.

Requirements:
- Order topics so that no section requires knowledge not covered in a prior section.
- For STEM subjects, prerequisite ordering is critical — enforce it strictly.
- Mark sections as core or supplementary based on depth requested.
- Identify which sections need a diagram and which need a code example.
- For "survey" depth: include only core sections.
- For "standard" depth: include core + key supplementary sections.
- For "deep" depth: include everything.
- Adapt content style to the learner's learning style preference.
- Where possible, use the learner's interests to choose relatable examples.

Return your response as a valid JSON object conforming to the CurriculumPlan schema.
"""
