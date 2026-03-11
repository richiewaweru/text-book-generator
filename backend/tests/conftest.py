import json
from pathlib import Path

import pytest

from textbook_agent.domain.entities.learner_profile import LearnerProfile

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def beginner_profile() -> LearnerProfile:
    data = json.loads((FIXTURES_DIR / "stem_beginner.json").read_text())
    return LearnerProfile.model_validate(data)


@pytest.fixture
def intermediate_profile() -> LearnerProfile:
    data = json.loads((FIXTURES_DIR / "stem_intermediate.json").read_text())
    return LearnerProfile.model_validate(data)


@pytest.fixture
def advanced_profile() -> LearnerProfile:
    data = json.loads((FIXTURES_DIR / "stem_advanced.json").read_text())
    return LearnerProfile.model_validate(data)
