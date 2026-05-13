"""Initial database baseline.

Revision ID: 202605130001
Revises:
Create Date: 2026-05-13
"""

from collections.abc import Sequence

revision: str = "202605130001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
