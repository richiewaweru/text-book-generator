"""add unit_capability_declarations and backfill from intake + active path

Revision ID: 20260806_0032
Revises: 20260803_0031

Migration choice: backfill. Existing units get confirmed teacher_intake rows from
starting_knowledge and assumed_prerequisites, plus unconfirmed path_planner rows
from active-path external_prerequisites that are not already present.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260806_0032"
down_revision = "20260803_0031"
branch_labels = None
depends_on = None


def _json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def upgrade() -> None:
    op.create_table(
        "unit_capability_declarations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("unit_id", sa.String(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_unit_capability_declarations_unit_id",
        "unit_capability_declarations",
        ["unit_id"],
        unique=False,
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_unit_capability_declarations_unit_lower_label "
            "ON unit_capability_declarations (unit_id, lower(label))"
        )
    )

    bind = op.get_bind()
    units = bind.execute(
        sa.text("SELECT id, starting_knowledge, active_path_version_id FROM units")
    ).mappings().all()
    scopes = {
        row["unit_id"]: row["assumed_prerequisites"]
        for row in bind.execute(
            sa.text("SELECT unit_id, assumed_prerequisites FROM unit_scope_contracts")
        ).mappings()
    }

    now = _utcnow()
    for unit in units:
        unit_id = unit["id"]
        seen: set[str] = set()
        for label in [
            *_as_list(unit["starting_knowledge"]),
            *_as_list(scopes.get(unit_id)),
        ]:
            folded = label.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            bind.execute(
                sa.text(
                    """
                    INSERT INTO unit_capability_declarations
                        (id, unit_id, label, source, confirmed, confirmed_at, created_at)
                    VALUES
                        (:id, :unit_id, :label, 'teacher_intake', true, :confirmed_at, :created_at)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "unit_id": unit_id,
                    "label": label,
                    "confirmed_at": now,
                    "created_at": now,
                },
            )

        active_version_id = unit["active_path_version_id"]
        if not active_version_id:
            continue
        lessons = bind.execute(
            sa.text(
                """
                SELECT external_prerequisites
                FROM path_lessons
                WHERE path_version_id = :version_id
                ORDER BY position
                """
            ),
            {"version_id": active_version_id},
        ).mappings().all()
        for lesson in lessons:
            for label in _as_list(lesson["external_prerequisites"]):
                folded = label.casefold()
                if folded in seen:
                    continue
                seen.add(folded)
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO unit_capability_declarations
                            (id, unit_id, label, source, confirmed, confirmed_at, created_at)
                        VALUES
                            (:id, :unit_id, :label, 'path_planner', false, NULL, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "unit_id": unit_id,
                        "label": label,
                        "created_at": now,
                    },
                )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS uq_unit_capability_declarations_unit_lower_label"
        )
    )
    op.drop_index(
        "ix_unit_capability_declarations_unit_id",
        table_name="unit_capability_declarations",
    )
    op.drop_table("unit_capability_declarations")
