"""Create human approvals table.

Revision ID: 202605160002
Revises: 202605160001
Create Date: 2026-05-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605160002"
down_revision: str | None = "202605160001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "human_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("policy_decision_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "expired",
                "cancelled",
                name="human_approval_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "requested_by_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="human_approval_requested_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("requested_by_actor_id", sa.String(length=255), nullable=False),
        sa.Column(
            "reviewed_by_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="human_approval_reviewed_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("reviewed_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["policy_decision_id"], ["policy_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("human_approvals")
