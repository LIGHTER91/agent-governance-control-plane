"""Add policy review assignment fields.

Revision ID: 202606090003
Revises: 202606090002
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090003"
down_revision: str | None = "202606090002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_version_review_requests",
        sa.Column(
            "assigned_reviewer_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="policy_version_review_assigned_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "policy_version_review_requests",
        sa.Column("assigned_reviewer_actor_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "policy_version_review_requests",
        sa.Column("assigned_reviewer_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "policy_version_review_requests",
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "policy_version_review_requests",
        sa.Column(
            "assigned_by_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="policy_version_review_assigned_by_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "policy_version_review_requests",
        sa.Column("assigned_by_actor_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_version_review_requests", "assigned_by_actor_id")
    op.drop_column("policy_version_review_requests", "assigned_by_actor_type")
    op.drop_column("policy_version_review_requests", "assigned_at")
    op.drop_column("policy_version_review_requests", "assigned_reviewer_name")
    op.drop_column("policy_version_review_requests", "assigned_reviewer_actor_id")
    op.drop_column("policy_version_review_requests", "assigned_reviewer_actor_type")
