"""Create policy check steps table.

Revision ID: 202605280001
Revises: 202605260002
Create Date: 2026-05-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605280001"
down_revision: str | None = "202605260002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_check_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_rule_id", sa.Uuid(), nullable=False),
        sa.Column("check_tool_id", sa.Uuid(), nullable=True),
        sa.Column(
            "check_type",
            sa.Enum(
                "access_grant_status",
                "data_usage_profile_status",
                "source_status",
                "capability_status",
                "model_asset_status",
                name="policy_check_step_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "target_selector",
            sa.Enum(
                "agent",
                "source_ids",
                "model_id",
                "capability_id",
                "access_grants",
                name="policy_check_step_target_selector",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "required", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "failure_behavior",
            sa.Enum(
                "record_only",
                "require_human_review",
                "fail_closed",
                "ignore_if_unavailable",
                name="policy_check_step_failure_behavior",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("min_confidence", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "disabled",
                "retired",
                name="policy_check_step_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "evidence_retention",
            sa.Enum(
                "decision_only",
                "evidence_bundle",
                "none",
                name="policy_check_step_evidence_retention",
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
        sa.ForeignKeyConstraint(["check_tool_id"], ["check_tools.id"]),
        sa.ForeignKeyConstraint(["policy_rule_id"], ["policy_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("policy_check_steps")
