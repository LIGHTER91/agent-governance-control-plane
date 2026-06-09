"""Add single active policy version guard.

Revision ID: 202606090001
Revises: 202606010002
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606090001"
down_revision: str | None = "202606010002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_policy_versions_one_active_per_policy",
        "policy_versions",
        ["policy_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_policy_versions_one_active_per_policy",
        table_name="policy_versions",
    )
