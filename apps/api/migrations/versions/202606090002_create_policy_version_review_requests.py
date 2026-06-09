"""Create policy version review requests table.

Revision ID: 202606090002
Revises: 202606090001
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090002"
down_revision: str | None = "202606090001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_version_review_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "canceled",
                name="policy_version_review_request_status",
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
                name="policy_version_review_requested_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("requested_by_actor_id", sa.String(length=255), nullable=False),
        sa.Column(
            "reviewer_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="policy_version_review_reviewer_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("reviewer_actor_id", sa.String(length=255), nullable=True),
        sa.Column("request_note", sa.Text(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"]),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_policy_version_review_requests_one_pending_per_version",
        "policy_version_review_requests",
        ["policy_version_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_policy_version_review_requests_one_pending_per_version",
        table_name="policy_version_review_requests",
    )
    op.drop_table("policy_version_review_requests")
