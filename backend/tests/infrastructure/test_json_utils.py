from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.infrastructure.providers.json_utils import extract_json, to_strict_json_schema


def test_to_strict_json_schema_closes_objects_and_strips_defaults():
    schema = to_strict_json_schema(SectionContent.model_json_schema())
    plan_schema = to_strict_json_schema(CurriculumPlan.model_json_schema())

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())
    assert "default" not in schema["properties"]["prerequisites_block"]
    assert "title" not in schema
    assert schema["$defs"]["PracticeProblem"]["additionalProperties"] is False
    assert set(schema["$defs"]["PracticeProblem"]["required"]) == {
        "difficulty",
        "statement",
        "hint",
    }
    assert "title" in plan_schema["$defs"]["SectionSpec"]["properties"]


def test_extract_json_parses_json_with_preface_and_suffix():
    payload = 'Here is the result:\n{"passed": true, "issues": []}\nThanks.'

    parsed = extract_json(payload)

    assert parsed == {"passed": True, "issues": []}
