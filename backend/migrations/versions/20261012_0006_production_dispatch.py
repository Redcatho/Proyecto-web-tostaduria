"""Add production and dispatch operations.

Revision ID: 20261012_0006
Revises: 20261012_0005
"""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0006"
down_revision = "20261012_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("production_started_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("production_started_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("production_notes", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("return_reason", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_orders_production_started_by", "users", ["production_started_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_table("dispatch_guides", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("prepared_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("carrier_name", sa.String(160), nullable=False), sa.Column("tracking_number", sa.String(120)), sa.Column("dispatch_note", sa.String(1000)), sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False), sa.Column("delivered_at", sa.DateTime(timezone=True)), sa.Column("delivery_confirmed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")))


def downgrade() -> None:
    op.drop_table("dispatch_guides")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_production_started_by", type_="foreignkey")
        for column in ("returned_at", "delivered_at", "return_reason", "production_notes", "production_started_by_user_id", "production_started_at"):
            batch.drop_column(column)
