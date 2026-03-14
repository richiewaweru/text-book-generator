import asyncio

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.prompts.planner_prompts import build_planner_prompt
from .node_base import PipelineNode


class CurriculumPlannerNode(PipelineNode[GenerationContext, CurriculumPlan]):
    """Node 1: Determines curriculum structure from a generation context."""

    input_schema = GenerationContext
    output_schema = CurriculumPlan

    def __init__(self, provider=None, model_override: str | None = None) -> None:
        super().__init__(provider=provider)
        self.model_override = model_override

    async def run(self, input_data: GenerationContext) -> CurriculumPlan:
        prompt = build_planner_prompt(input_data)
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Create a curriculum plan for: {input_data.subject}",
            response_schema=CurriculumPlan,
            model=self.model_override,
        )
