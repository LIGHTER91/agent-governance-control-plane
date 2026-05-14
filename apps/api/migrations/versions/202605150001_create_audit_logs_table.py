"""Create audit logs table.

Revision ID: 202605150001
Revises: 202605130002
Create Date: 2026-05-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605150001"
down_revision: str | None = "202605130002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column(
            "actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="audit_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=255), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
