from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.models import Cart, CartItem, CreditTerms, ProductVariant
from app.services.catalog import current_exchange_rate, variant_stock

ROAST_PROFILES = {"claro", "medio", "medio_alto", "alto"}
DELIVERY_METHODS = {"pickup", "local_delivery", "national_carrier"}
PAYMENT_CONDITIONS = {"full_payment", "advance_50", "credit"}


class CommerceValidationError(ValueError):
    pass


def get_cart(user_id: int, create: bool = True) -> Cart | None:
    cart = db.session.scalar(db.select(Cart).where(Cart.user_id == user_id))
    if cart is None and create:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart


def cart_summary(cart: Cart) -> dict:
    cafe_total_kg = sum((Decimal(item.quantity) for item in cart.items if item.variant.product.line == "cafeteria"), Decimal("0"))
    discount_per_kg = Decimal("2") if cafe_total_kg > 100 else Decimal("1") if cafe_total_kg > 50 else Decimal("0")
    subtotal = Decimal("0")
    discount = Decimal("0")
    items = []
    for item in cart.items:
        variant = item.variant
        unit_price = Decimal(variant.price_usd)
        item_discount = discount_per_kg if variant.product.line == "cafeteria" else Decimal("0")
        line_subtotal = (unit_price * Decimal(item.quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line_discount = (item_discount * Decimal(item.quantity)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += line_subtotal
        discount += line_discount
        items.append({"id": item.id, "variant_id": variant.id, "product_name": variant.product.name, "variant_name": variant.name, "line": variant.product.line, "quantity": str(item.quantity), "unit": variant.sale_unit, "roast_profile": item.roast_profile, "customer_note": item.customer_note, "unit_price_usd": str(unit_price), "discount_per_unit_usd": str(item_discount), "line_total_usd": str(line_subtotal - line_discount), "availability_stock": str(variant_stock(variant.id))})
    rate = current_exchange_rate()
    total = (subtotal - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"items": items, "cafe_total_kg": str(cafe_total_kg), "discount_per_kg": str(discount_per_kg), "subtotal_usd": str(subtotal), "discount_usd": str(discount), "total_usd": str(total), "total_ves": str((total * Decimal(rate.rate_ves)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if rate else None, "exchange_rate": {"rate_ves": str(rate.rate_ves), "effective_date": rate.effective_date.isoformat()} if rate else None}


def validate_cart(cart: Cart) -> dict:
    if not cart.items:
        raise CommerceValidationError("The cart is empty.")
    summary = cart_summary(cart)
    roast_totals: dict[str, Decimal] = {}
    commercial_bultos = Decimal("0")
    cafe_total = Decimal("0")
    for item in cart.items:
        variant = item.variant
        quantity = Decimal(item.quantity)
        if not variant.is_active or not variant.product.is_active:
            raise CommerceValidationError(f"{variant.product.name} is no longer available.")
        if variant.product.line == "commercial":
            if quantity != quantity.to_integral_value():
                raise CommerceValidationError("Commercial products must be requested in whole bundles.")
            commercial_bultos += quantity
        else:
            if quantity < 5 or quantity % 5 != 0:
                raise CommerceValidationError("Coffee for cafeterias requires multiples of 5 kg per quality.")
            if item.roast_profile not in ROAST_PROFILES:
                raise CommerceValidationError("Choose a valid roast profile for coffee for cafeterias.")
            cafe_total += quantity
            roast_totals[item.roast_profile] = roast_totals.get(item.roast_profile, Decimal("0")) + quantity
        # Stock is not validated against customer orders; inventory is informational for staff only.
    if cafe_total > 20 and len(roast_totals) > 1 and any(quantity < 10 for quantity in roast_totals.values()):
        raise CommerceValidationError("Orders above 20 kg with multiple roast profiles require at least 10 kg per profile.")
    if summary["exchange_rate"] is None:
        raise CommerceValidationError("A current BCV exchange rate is required before issuing a quote.")
    if commercial_bultos > 10:
        hours, note = None, "Commercial orders above 10 bundles require administrative review."
    else:
        hours = 48 if cafe_total > 100 else 24
        note = "Estimate begins after payment, advance or approved credit is confirmed."
    summary["estimated_dispatch_hours"] = hours
    summary["estimate_note"] = note
    return summary


def credit_terms_for_business(business_id: int):
    return db.session.scalar(db.select(CreditTerms).where(CreditTerms.business_id == business_id, CreditTerms.is_active.is_(True)).order_by(CreditTerms.id.desc()))


def required_advance(total: Decimal, payment_condition: str, business_id: int) -> Decimal:
    if payment_condition not in PAYMENT_CONDITIONS:
        raise CommerceValidationError("Invalid payment condition.")
    if payment_condition == "full_payment":
        return total
    if payment_condition == "advance_50":
        return (total * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if credit_terms_for_business(business_id) is None:
        raise CommerceValidationError("This business does not have approved credit terms.")
    return Decimal("0")


def quote_expiration() -> datetime:
    return datetime.now(UTC) + timedelta(hours=24)
