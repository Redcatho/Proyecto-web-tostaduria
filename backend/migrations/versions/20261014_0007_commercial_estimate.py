"""Add estimated_dispatch_hours and estimate_note to orders.

Revision ID: 20261014_0007
Revises: 20261012_0006
"""

from alembic import op
import sqlalchemy as sa

revision = "20261014_0007"
down_revision = "20261012_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("estimated_dispatch_hours", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("estimate_note", sa.String(500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("estimate_note")
        batch.drop_column("estimated_dispatch_hours")