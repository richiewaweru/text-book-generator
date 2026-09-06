from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/core/database/migrations/versions/20260906_0035_repair_unit_capability_declarations.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("capability_declaration_repair", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_repair_migration_restores_table_on_false_head_and_is_idempotent() -> None:
    migration = _load_migration()
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        # Model the affected state: all predecessor tables exist, but the
        # database was incorrectly stamped at 0034 with the 0032 table absent.
        connection.execute(
            text(
                "CREATE TABLE units ("
                "id VARCHAR PRIMARY KEY, starting_knowledge JSON, "
                "active_path_version_id VARCHAR)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE unit_scope_contracts ("
                "unit_id VARCHAR PRIMARY KEY, assumed_prerequisites JSON)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE path_lessons ("
                "path_version_id VARCHAR, position INTEGER, "
                "external_prerequisites JSON)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO units (id, starting_knowledge, active_path_version_id) "
                "VALUES ('unit-1', '[\"fractions\"]', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO unit_scope_contracts (unit_id, assumed_prerequisites) "
                "VALUES ('unit-1', '[\"Fractions\", \"decimals\"]')"
            )
        )
        operations = Operations(MigrationContext.configure(connection))
        migration.op = operations

        migration.upgrade()
        assert inspect(connection).has_table("unit_capability_declarations")
        columns = {column["name"] for column in inspect(connection).get_columns("unit_capability_declarations")}
        assert columns == {
            "id",
            "unit_id",
            "label",
            "source",
            "confirmed",
            "confirmed_at",
            "created_at",
        }
        rows = connection.execute(
            text(
                "SELECT label, source, confirmed FROM unit_capability_declarations "
                "ORDER BY label"
            )
        ).all()
        assert rows == [
            ("decimals", "teacher_intake", 1),
            ("fractions", "teacher_intake", 1),
        ]

        # A retry after a partially completed deployment must not collide with
        # existing table/index objects or duplicate backfill rows.
        migration.upgrade()
        index_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'index' AND tbl_name = 'unit_capability_declarations'"
                )
            )
        }
        assert {
            "ix_unit_capability_declarations_unit_id",
            "uq_unit_capability_declarations_unit_lower_label",
        } <= index_names

        # Rollback must preserve declarations recovered by this repair.
        migration.downgrade()
        assert inspect(connection).has_table("unit_capability_declarations")
