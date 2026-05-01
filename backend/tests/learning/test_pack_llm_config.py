from core.llm import ModelFamily, ModelSlot
from planning.llm_config import get_planning_slot, get_planning_spec


def test_learning_pack_callers_use_fast_haiku_defaults():
    for caller in ("learning_job_interpreter", "pack_learning_planner"):
        spec = get_planning_spec(caller)

        assert get_planning_slot(caller) == ModelSlot.FAST
        assert spec.family == ModelFamily.ANTHROPIC
        assert spec.model_name == "claude-haiku-4-5-20251001"
