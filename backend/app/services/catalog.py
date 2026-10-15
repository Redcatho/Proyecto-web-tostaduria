from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app.extensions import db
from app.models import ExchangeRate, InventoryBalance, ProductVariant


def variant_stock(variant_id: int) -> Decimal:
    value = db.session.scalar(
        db.select(func.coalesce(func.sum(InventoryBalance.quantity), 0)).where(InventoryBalance.variant_id == variant_id)
    )
    return Decimal(value)


def availability_label(variant: ProductVariant, stock: Decimal) -> str:
    if not variant.is_active or not variant.product.is_active:
        return "Agotado"
    if variant.product.availability_mode == "made_to_order":
        return "Bajo pedido"
    return "Disponible"


def current_exchange_rate() -> ExchangeRate | None:
    return db.session.scalar(db.select(ExchangeRate).where(ExchangeRate.currency == "USD").order_by(ExchangeRate.effective_date.desc()))


def product_payload(product, include_stock: bool = False, rate: ExchangeRate | None = None) -> dict:
    rate = rate if rate is not None else current_exchange_rate()
    variants = []
    for variant in product.variants:
        stock = variant_stock(variant.id)
        price_ves = None
        if rate:
            price_ves = (Decimal(variant.price_usd) * Decimal(rate.rate_ves)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        item = {
            "id": variant.id,
            "sku": variant.sku,
            "name": variant.name,
            "quality_code": variant.quality_code,
            "sale_unit": variant.sale_unit,
            "inventory_unit": variant.inventory_unit,
            "unit_weight_kg": str(variant.unit_weight_kg),
            "packages_per_unit": variant.packages_per_unit,
            "price_usd": str(variant.price_usd),
            "price_ves": str(price_ves) if price_ves is not None else None,
            "availability": availability_label(variant, stock),
        }
        if include_stock:
            item["stock"] = str(stock)
            item["low_stock_threshold"] = str(variant.low_stock_threshold)
        variants.append(item)
    return {
        "id": product.id,
        "slug": product.slug,
        "line": product.line,
        "name": product.name,
        "description": product.description,
        "coffee_type": product.coffee_type,
        "variety": product.variety,
        "origin": product.origin,
        "sensory_notes": product.sensory_notes,
        "image_url": product.image_url,
        "is_active": product.is_active,
        "variants": variants,
    }
