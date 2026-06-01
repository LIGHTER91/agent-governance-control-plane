"""Add policy version reference to policy decisions.

Revision ID: 202606010002
Revises: 202606010001
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606010002"
down_revision: str | None = "202606010001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_decisions",
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_policy_decisions_policy_version",
        "policy_decisions",
        "policy_versions",
        ["policy_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_policy_decisions_policy_version",
        "policy_decisions",
        type_="foreignkey",
    )
    op.drop_column("policy_decisions", "policy_version_id")
