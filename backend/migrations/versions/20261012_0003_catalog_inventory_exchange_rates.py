"""Add catalog, inventory and BCV exchange rates.

Revision ID: 20261012_0003
Revises: 20261012_0002
Create Date: 2026-10-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "20261012_0003"
down_revision = "20261012_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    seeded_at = datetime(2026, 10, 12)
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=160), nullable=False, unique=True),
        sa.Column("line", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("coffee_type", sa.String(length=120)),
        sa.Column("variety", sa.String(length=120)),
        sa.Column("origin", sa.String(length=180)),
        sa.Column("sensory_notes", sa.Text()),
        sa.Column("image_url", sa.String(length=500)),
        sa.Column("availability_mode", sa.String(length=24), nullable=False, server_default="auto"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_slug", "products", ["slug"])
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("quality_code", sa.String(length=24)),
        sa.Column("sale_unit", sa.String(length=16), nullable=False),
        sa.Column("inventory_unit", sa.String(length=16), nullable=False),
        sa.Column("unit_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("packages_per_unit", sa.Integer()),
        sa.Column("price_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(10, 3), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_variants_sku", "product_variants", ["sku"])
    op.create_table(
        "inventory_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("variant_id", "location_id", name="uq_inventory_balance"),
    )
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("inventory_locations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(12, 3), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("rate_ves", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_method", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500)),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.UniqueConstraint("currency", "effective_date", name="uq_exchange_rate_date"),
    )
    op.bulk_insert(
        sa.table("inventory_locations", sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime)),
        [{"id": 1, "name": "Almacén principal", "is_active": True, "created_at": seeded_at}],
    )
    op.bulk_insert(
        sa.table("products", sa.column("id", sa.Integer), sa.column("slug", sa.String), sa.column("line", sa.String), sa.column("name", sa.String), sa.column("description", sa.Text), sa.column("availability_mode", sa.String), sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime)),
        [
            {"id": 1, "slug": "comercial-molido-200g", "line": "commercial", "name": "Café comercial molido 200 g", "description": "Bulto rotulado de 40 empaques de 200 g.", "availability_mode": "auto", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 2, "slug": "comercial-molido-500g", "line": "commercial", "name": "Café comercial molido 500 g", "description": "Bulto rotulado de 20 empaques de 500 g.", "availability_mode": "auto", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 3, "slug": "comercial-grano-500g", "line": "commercial", "name": "Café comercial en grano 500 g", "description": "Bulto rotulado de 20 empaques de 500 g en grano.", "availability_mode": "auto", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 4, "slug": "cafeterias-calidad-menor", "line": "cafeteria", "name": "Café para cafeterías · Calidad menor", "description": "Café en grano sin marca para operación de cafeterías.", "availability_mode": "made_to_order", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 5, "slug": "cafeterias-calidad-media", "line": "cafeteria", "name": "Café para cafeterías · Calidad media", "description": "Café en grano sin marca para operación de cafeterías.", "availability_mode": "made_to_order", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 6, "slug": "cafeterias-calidad-superior", "line": "cafeteria", "name": "Café para cafeterías · Calidad superior", "description": "Café en grano sin marca para operación de cafeterías.", "availability_mode": "made_to_order", "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
        ],
    )
    op.bulk_insert(
        sa.table("product_variants", sa.column("id", sa.Integer), sa.column("product_id", sa.Integer), sa.column("sku", sa.String), sa.column("name", sa.String), sa.column("quality_code", sa.String), sa.column("sale_unit", sa.String), sa.column("inventory_unit", sa.String), sa.column("unit_weight_kg", sa.Numeric), sa.column("packages_per_unit", sa.Integer), sa.column("price_usd", sa.Numeric), sa.column("low_stock_threshold", sa.Numeric), sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime)),
        [
            {"id": 1, "product_id": 1, "sku": "COM-MOL-200-B40", "name": "Bulto 40 x 200 g", "quality_code": None, "sale_unit": "bulto", "inventory_unit": "bulto", "unit_weight_kg": 8, "packages_per_unit": 40, "price_usd": 180, "low_stock_threshold": 3, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 2, "product_id": 2, "sku": "COM-MOL-500-B20", "name": "Bulto 20 x 500 g", "quality_code": None, "sale_unit": "bulto", "inventory_unit": "bulto", "unit_weight_kg": 10, "packages_per_unit": 20, "price_usd": 260, "low_stock_threshold": 3, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 3, "product_id": 3, "sku": "COM-GRA-500-B20", "name": "Bulto 20 x 500 g", "quality_code": None, "sale_unit": "bulto", "inventory_unit": "bulto", "unit_weight_kg": 10, "packages_per_unit": 20, "price_usd": 330, "low_stock_threshold": 3, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 4, "product_id": 4, "sku": "CAF-MEN-1KG", "name": "Empaque sin marca de 1 kg", "quality_code": "lower", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": 1, "packages_per_unit": 1, "price_usd": 21, "low_stock_threshold": 5, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 5, "product_id": 5, "sku": "CAF-MED-1KG", "name": "Empaque sin marca de 1 kg", "quality_code": "medium", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": 1, "packages_per_unit": 1, "price_usd": 25, "low_stock_threshold": 5, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
            {"id": 6, "product_id": 6, "sku": "CAF-SUP-1KG", "name": "Empaque sin marca de 1 kg", "quality_code": "superior", "sale_unit": "kg", "inventory_unit": "kg", "unit_weight_kg": 1, "packages_per_unit": 1, "price_usd": 30, "low_stock_threshold": 5, "is_active": True, "created_at": seeded_at, "updated_at": seeded_at},
        ],
    )


def downgrade() -> None:
    for table in ("exchange_rates", "inventory_movements", "inventory_balances", "inventory_locations", "product_variants", "products"):
        op.drop_table(table)
