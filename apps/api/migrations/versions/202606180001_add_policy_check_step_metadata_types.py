"""Add metadata-only PolicyCheckStep check types.

Revision ID: 202606180001
Revises: 202606090003
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202606180001"
down_revision: str | None = "202606090003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY_CHECK_STEP_TYPES_WITH_METADATA = (
    "'access_grant_status'",
    "'data_usage_profile_status'",
    "'source_status'",
    "'source_classification'",
    "'capability_status'",
    "'model_asset_status'",
    "'model_provider_type'",
)
POLICY_CHECK_STEP_TYPES_BEFORE_METADATA = (
    "'access_grant_status'",
    "'data_usage_profile_status'",
    "'source_status'",
    "'capability_status'",
    "'model_asset_status'",
)


def upgrade() -> None:
    op.drop_constraint(
        "policy_check_step_type",
        "policy_check_steps",
        type_="check",
    )
    op.create_check_constraint(
        "policy_check_step_type",
        "policy_check_steps",
        f"check_type IN ({', '.join(POLICY_CHECK_STEP_TYPES_WITH_METADATA)})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "policy_check_step_type",
        "policy_check_steps",
        type_="check",
    )
    op.create_check_constraint(
        "policy_check_step_type",
        "policy_check_steps",
        f"check_type IN ({', '.join(POLICY_CHECK_STEP_TYPES_BEFORE_METADATA)})",
    )
