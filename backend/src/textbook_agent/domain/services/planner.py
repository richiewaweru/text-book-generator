import asyncio

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.prompts.planner_prompts import build_planner_prompt
from .node_base import PipelineNode


class CurriculumPlannerNode(PipelineNode[LearnerProfile, CurriculumPlan]):
    """Node 1: Determines curriculum structure from a learner profile."""

    input_schema = LearnerProfile
    output_schema = CurriculumPlan

    async def run(self, input_data: LearnerProfile) -> CurriculumPlan:
        prompt = build_planner_prompt(input_data)
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Create a curriculum plan for: {input_data.subject}",
            response_schema=CurriculumPlan,
        )
