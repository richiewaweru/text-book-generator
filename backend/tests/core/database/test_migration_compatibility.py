from __future__ import annotations

from alembic.script import ScriptDirectory

from core.database.migrations.runner import _alembic_config


def test_v3_recognizes_shared_xplore_database_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())

    assert script.get_current_head() == "20260801_0028"
    assert script.get_revision("20260801_0028").down_revision == "20260801_0027"
    assert script.get_revision("20260731_0017").down_revision == "20260727_0016"
