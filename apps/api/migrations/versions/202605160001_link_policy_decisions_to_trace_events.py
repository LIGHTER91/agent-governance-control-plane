"""Link policy decisions to trace events.

Revision ID: 202605160001
Revises: 202605150003
Create Date: 2026-05-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605160001"
down_revision: str | None = "202605150003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_decisions",
        sa.Column("trace_event_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_policy_decisions_trace_event",
        "policy_decisions",
        "trace_events",
        ["trace_event_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_policy_decisions_trace_event",
        "policy_decisions",
        type_="foreignkey",
    )
    op.drop_column("policy_decisions", "trace_event_id")
