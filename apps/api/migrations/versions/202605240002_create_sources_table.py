"""Create sources table.

Revision ID: 202605240002
Revises: 202605240001
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605240002"
down_revision: str | None = "202605240001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum(
                "knowledge_base",
                "database",
                "document_store",
                "api",
                "bucket",
                "filesystem",
                "other",
                name="source_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("external_ref", sa.String(length=512), nullable=True),
        sa.Column(
            "owner_type",
            sa.Enum(
                "user",
                "team",
                "service",
                "organization_unit",
                name="source_owner_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("owner_contact_email", sa.String(length=320), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "disabled",
                "retired",
                name="source_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "risk_level",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="source_risk_level",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sources")
