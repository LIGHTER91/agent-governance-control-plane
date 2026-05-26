"""Create policy pre-check tables.

Revision ID: 202605260002
Revises: 202605260001
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605260002"
down_revision: str | None = "202605260001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "check_tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "tool_type",
            sa.Enum(
                "metadata_lookup",
                "access_grant_check",
                "data_usage_profile_check",
                "source_status_check",
                "model_status_check",
                "capability_status_check",
                name="check_tool_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "disabled",
                "retired",
                name="check_tool_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "owner_type",
            sa.Enum(
                "user",
                "team",
                "service",
                "organization_unit",
                name="check_tool_owner_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("name", name="uq_check_tools_name"),
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("check_tool_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("trace_event_id", sa.Uuid(), nullable=True),
        sa.Column("policy_decision_id", sa.Uuid(), nullable=True),
        sa.Column(
            "target_type",
            sa.Enum(
                "source",
                "capability",
                "model_asset",
                "access_grant",
                "data_usage_profile",
                "external",
                name="check_result_target_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum(
                "pass",
                "fail",
                "unknown",
                "error",
                "not_applicable",
                name="check_result_outcome",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Enum(
                "high",
                "medium",
                "low",
                "unknown",
                name="check_result_confidence",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["check_tool_id"], ["check_tools.id"]),
        sa.ForeignKeyConstraint(["policy_decision_id"], ["policy_decisions.id"]),
        sa.ForeignKeyConstraint(["trace_event_id"], ["trace_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("check_results")
    op.drop_table("check_tools")
