"""Create service actor scope tables.

Revision ID: 202605220001
Revises: 202605210001
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605220001"
down_revision: str | None = "202605210001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_actor_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_actor_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["service_actor_id"], ["service_actors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "service_actor_id",
            "scope",
            name="uq_service_actor_scopes_actor_scope",
        ),
    )
    op.create_table(
        "service_actor_scope_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_actor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "agent_ids", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
        sa.Column(
            "environments",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "runtime_modes",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "tool_names", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["service_actor_id"], ["service_actors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("service_actor_scope_rules")
    op.drop_table("service_actor_scopes")
