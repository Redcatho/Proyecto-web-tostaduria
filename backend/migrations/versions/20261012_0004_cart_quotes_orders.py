"""Add carts, quotes and initial orders.

Revision ID: 20261012_0004
Revises: 20261012_0003
Create Date: 2026-10-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0004"
down_revision = "20261012_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("carts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("cart_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False), sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False), sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("roast_profile", sa.String(24)), sa.Column("customer_note", sa.String(1000)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("cart_id", "variant_id", "roast_profile", name="uq_cart_item_configuration"))
    op.create_table("quotes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("number", sa.String(32), nullable=False, unique=True), sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("delivery_method", sa.String(24), nullable=False), sa.Column("delivery_address_id", sa.Integer(), sa.ForeignKey("business_addresses.id", ondelete="SET NULL")), sa.Column("payment_condition", sa.String(32), nullable=False), sa.Column("rate_ves", sa.Numeric(14, 2), nullable=False), sa.Column("rate_effective_date", sa.Date(), nullable=False), sa.Column("subtotal_usd", sa.Numeric(14, 2), nullable=False), sa.Column("discount_usd", sa.Numeric(14, 2), nullable=False), sa.Column("total_usd", sa.Numeric(14, 2), nullable=False), sa.Column("total_ves", sa.Numeric(16, 2), nullable=False), sa.Column("required_advance_usd", sa.Numeric(14, 2), nullable=False), sa.Column("estimated_dispatch_hours", sa.Integer()), sa.Column("estimate_note", sa.String(500)), sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_quotes_number", "quotes", ["number"])
    op.create_table("quote_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("quote_id", sa.Integer(), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False), sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="SET NULL")), sa.Column("sku_snapshot", sa.String(80), nullable=False), sa.Column("product_name_snapshot", sa.String(180), nullable=False), sa.Column("line_snapshot", sa.String(24), nullable=False), sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("roast_profile", sa.String(24)), sa.Column("customer_note", sa.String(1000)), sa.Column("unit_price_usd", sa.Numeric(12, 2), nullable=False), sa.Column("discount_per_unit_usd", sa.Numeric(12, 2), nullable=False), sa.Column("line_total_usd", sa.Numeric(14, 2), nullable=False))
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("number", sa.String(32), nullable=False, unique=True), sa.Column("quote_id", sa.Integer(), sa.ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, unique=True), sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_orders_number", "orders", ["number"])
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("quote_item_id", sa.Integer(), sa.ForeignKey("quote_items.id", ondelete="SET NULL")), sa.Column("sku_snapshot", sa.String(80), nullable=False), sa.Column("product_name_snapshot", sa.String(180), nullable=False), sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("roast_profile", sa.String(24)), sa.Column("customer_note", sa.String(1000)), sa.Column("unit_price_usd", sa.Numeric(12, 2), nullable=False), sa.Column("discount_per_unit_usd", sa.Numeric(12, 2), nullable=False), sa.Column("line_total_usd", sa.Numeric(14, 2), nullable=False))
    op.create_table("order_status_history", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("note", sa.String(1000)), sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    for table in ("order_status_history", "order_items", "orders", "quote_items", "quotes", "cart_items", "carts"):
        op.drop_table(table)
