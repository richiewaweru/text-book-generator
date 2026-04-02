"""add pdf metadata fields

Revision ID: 20260402_0008
Revises: 20260401_0007
Create Date: 2026-04-02 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260402_0008"
down_revision = "20260401_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("question_records", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "generations",
        sa.Column("sections_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generations", "sections_metadata")
    op.drop_column("generations", "question_records")
