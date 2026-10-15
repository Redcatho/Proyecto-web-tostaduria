"""Initialize platform migration tracking.

Revision ID: 20261012_0001
Revises:
Create Date: 2026-10-12 00:00:00
"""

revision = "20261012_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Business tables are deliberately introduced in their corresponding phases.
    pass


def downgrade() -> None:
    pass
