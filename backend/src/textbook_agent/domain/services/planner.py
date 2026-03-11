from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from .node_base import PipelineNode


class CurriculumPlannerNode(PipelineNode[LearnerProfile, CurriculumPlan]):
    """Node 1: Determines curriculum structure from a learner profile."""

    input_schema = LearnerProfile
    output_schema = CurriculumPlan

    async def run(self, input_data: LearnerProfile) -> CurriculumPlan:
        raise NotImplementedError
