"""Create data usage profiles table.

Revision ID: 202605260001
Revises: 202605240004
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605260001"
down_revision: str | None = "202605240004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_usage_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column(
            "data_classification",
            sa.Enum(
                "public",
                "internal",
                "confidential",
                "restricted",
                name="data_usage_classification",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "contains_personal_data",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "contains_sensitive_data",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "data_categories",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("legal_basis", sa.Text(), nullable=True),
        sa.Column(
            "allowed_purposes",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "prohibited_purposes",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "allowed_processing",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "prohibited_processing",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("residency", sa.String(length=255), nullable=True),
        sa.Column("retention_policy", sa.String(length=255), nullable=True),
        sa.Column("data_owner", sa.String(length=255), nullable=True),
        sa.Column(
            "review_status",
            sa.Enum(
                "draft",
                "approved",
                "rejected",
                "expired",
                "needs_review",
                name="data_usage_review_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "reviewed_by_actor_type",
            sa.Enum(
                "system",
                "user",
                "service",
                "development",
                name="data_usage_profile_reviewed_actor_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("reviewed_by_actor_id", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "dpia_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("dpia_reference", sa.String(length=512), nullable=True),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            name="uq_data_usage_profiles_source_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("data_usage_profiles")
