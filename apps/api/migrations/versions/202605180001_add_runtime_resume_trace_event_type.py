"""Add runtime resume trace event type.

Revision ID: 202605180001
Revises: 202605160002
Create Date: 2026-05-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202605180001"
down_revision: str | None = "202605160002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRACE_EVENT_TYPES_WITH_RESUME = (
    "'model_call_started'",
    "'model_call_completed'",
    "'tool_call_requested'",
    "'tool_call_resume_requested'",
    "'tool_call_allowed'",
    "'tool_call_denied'",
    "'human_review_requested'",
    "'error'",
)
TRACE_EVENT_TYPES_WITHOUT_RESUME = (
    "'model_call_started'",
    "'model_call_completed'",
    "'tool_call_requested'",
    "'tool_call_allowed'",
    "'tool_call_denied'",
    "'human_review_requested'",
    "'error'",
)


def upgrade() -> None:
    op.drop_constraint("trace_event_type", "trace_events", type_="check")
    op.create_check_constraint(
        "trace_event_type",
        "trace_events",
        f"event_type IN ({', '.join(TRACE_EVENT_TYPES_WITH_RESUME)})",
    )


def downgrade() -> None:
    op.drop_constraint("trace_event_type", "trace_events", type_="check")
    op.create_check_constraint(
        "trace_event_type",
        "trace_events",
        f"event_type IN ({', '.join(TRACE_EVENT_TYPES_WITHOUT_RESUME)})",
    )
