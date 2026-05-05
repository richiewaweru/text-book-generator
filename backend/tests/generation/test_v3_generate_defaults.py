from generation.routes import V3GenerateRequest


def test_v3_generate_request_defaults_to_guided_concept_path() -> None:
    request = V3GenerateRequest(
        generation_id="gen-1",
        blueprint_id="bp-1",
        blueprint={},
    )
    assert request.template_id == "guided-concept-path"
