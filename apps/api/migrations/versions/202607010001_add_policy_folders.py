"""Add policy folders.

Revision ID: 202607010001
Revises: 202606180001
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607010001"
down_revision: str | None = "202606180001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column(
            "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
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
    op.add_column("policies", sa.Column("folder_id", sa.Uuid(), nullable=True))
    op.create_index("ix_policies_folder_id", "policies", ["folder_id"])
    op.create_foreign_key(
        "fk_policies_policy_folder",
        "policies",
        "policy_folders",
        ["folder_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_policies_policy_folder", "policies", type_="foreignkey")
    op.drop_index("ix_policies_folder_id", table_name="policies")
    op.drop_column("policies", "folder_id")
    op.drop_table("policy_folders")
