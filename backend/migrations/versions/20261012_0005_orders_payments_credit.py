"""Add order payment and credit tracking.

Revision ID: 20261012_0005
Revises: 20261012_0004
Create Date: 2026-10-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0005"
down_revision = "20261012_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("payment_condition", sa.String(32), nullable=True))
        batch.add_column(sa.Column("total_usd", sa.Numeric(14, 2), nullable=True))
        batch.add_column(sa.Column("total_ves", sa.Numeric(16, 2), nullable=True))
        batch.add_column(sa.Column("rate_ves", sa.Numeric(14, 2), nullable=True))
        batch.add_column(sa.Column("rate_effective_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("required_payment_usd", sa.Numeric(14, 2), nullable=True))
        batch.add_column(sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cancelled_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_orders_cancelled_by_user", "users", ["cancelled_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_table("payment_submissions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("currency", sa.String(8), nullable=False), sa.Column("amount", sa.Numeric(14, 2), nullable=False), sa.Column("amount_usd_equivalent", sa.Numeric(14, 2), nullable=False), sa.Column("reference", sa.String(120), nullable=False), sa.Column("payment_method", sa.String(40), nullable=False), sa.Column("proof_storage_key", sa.String(512), nullable=False, unique=True), sa.Column("proof_original_filename", sa.String(255), nullable=False), sa.Column("proof_content_type", sa.String(100), nullable=False), sa.Column("proof_size_bytes", sa.Integer(), nullable=False), sa.Column("note", sa.String(1000)), sa.Column("status", sa.String(24), nullable=False), sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("review_note", sa.String(1000)), sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_payment_submissions_order_id", "payment_submissions", ["order_id"])
    op.create_index("ix_payment_submissions_status", "payment_submissions", ["status"])
    op.create_table("credit_usages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("credit_terms_id", sa.Integer(), sa.ForeignKey("credit_terms.id", ondelete="RESTRICT"), nullable=False), sa.Column("amount_usd", sa.Numeric(14, 2), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("released_at", sa.DateTime(timezone=True)), sa.Column("released_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("release_note", sa.String(1000)))
    op.create_index("ix_credit_usages_business_id", "credit_usages", ["business_id"])
    op.create_index("ix_credit_usages_status", "credit_usages", ["status"])


def downgrade() -> None:
    op.drop_table("credit_usages")
    op.drop_table("payment_submissions")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_cancelled_by_user", type_="foreignkey")
        for column in ("cancelled_by_user_id", "cancelled_at", "confirmed_at", "required_payment_usd", "rate_effective_date", "rate_ves", "total_ves", "total_usd", "payment_condition"):
            batch.drop_column(column)
