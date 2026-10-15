from datetime import date
from decimal import Decimal
import re

from flask import Blueprint, jsonify
from flask_jwt_extended import get_current_user
import requests

from app.api.catalog.routes import rate_payload
from app.api.common import clean_text, error, json_body, parse_decimal
from app.extensions import db
from app.models import ExchangeRate, InventoryBalance, InventoryLocation, InventoryMovement, Product, ProductVariant
from app.security import audit, roles_required
from app.services.bcv import BcvRateError, save_exchange_rate, sync_official_bcv_rate
from app.services.catalog import current_exchange_rate, product_payload, variant_stock
from app.services.storage import StorageError, create_product_image_upload

catalog_admin_blueprint = Blueprint("catalog_admin", __name__)
PRODUCT_LINES = {"commercial", "cafeteria"}
AVAILABILITY_MODES = {"auto", "made_to_order"}
MOVEMENT_TYPES = {"incoming", "outgoing", "adjustment", "waste"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:160]


@catalog_admin_blueprint.get("/products")
@roles_required("admin", "sales", "operator")
def admin_products():
    rate = current_exchange_rate()
    products = db.session.scalars(db.select(Product).order_by(Product.line, Product.id)).all()
    return jsonify(products=[product_payload(product, include_stock=True, rate=rate) for product in products])


@catalog_admin_blueprint.post("/products")
@roles_required("admin")
def create_product():
    actor = get_current_user()
    data = json_body()
    line = clean_text(data.get("line"), 24)
    name = clean_text(data.get("name"), 180)
    if line not in PRODUCT_LINES or not name:
        return error("invalid_product", "A valid line and name are required.", 422)
    slug = slugify(clean_text(data.get("slug"), 160) or name)
    if not slug or db.session.scalar(db.select(Product).where(Product.slug == slug)):
        return error("slug_unavailable", "A unique product slug is required.", 409)
    product = Product(
        line=line,
        name=name,
        slug=slug,
        description=clean_text(data.get("description"), 2000) or None,
        coffee_type=clean_text(data.get("coffee_type"), 120) or None,
        variety=clean_text(data.get("variety"), 120) or None,
        origin=clean_text(data.get("origin"), 180) or None,
        sensory_notes=clean_text(data.get("sensory_notes"), 1000) or None,
        image_url=clean_text(data.get("image_url"), 500) or None,
        availability_mode=clean_text(data.get("availability_mode"), 24) if clean_text(data.get("availability_mode"), 24) in AVAILABILITY_MODES else "auto",
    )
    db.session.add(product)
    db.session.flush()
    audit(actor.id, "catalog.product_created", "product", product.id)
    db.session.commit()
    return jsonify(product=product_payload(product, include_stock=True)), 201


@catalog_admin_blueprint.patch("/products/<int:product_id>")
@roles_required("admin")
def update_product(product_id: int):
    actor = get_current_user()
    product = db.session.get(Product, product_id)
    if product is None:
        return error("not_found", "Product not found.", 404)
    data = json_body()
    text_fields = {"name": 180, "description": 2000, "coffee_type": 120, "variety": 120, "origin": 180, "sensory_notes": 1000, "image_url": 500}
    for field, length in text_fields.items():
        if field in data:
            setattr(product, field, clean_text(data[field], length) or None)
    if "availability_mode" in data:
        mode = clean_text(data["availability_mode"], 24)
        if mode not in AVAILABILITY_MODES:
            return error("invalid_availability_mode", "Availability mode is invalid.", 422)
        product.availability_mode = mode
    if "is_active" in data and isinstance(data["is_active"], bool):
        product.is_active = data["is_active"]
    audit(actor.id, "catalog.product_updated", "product", product.id)
    db.session.commit()
    return jsonify(product=product_payload(product, include_stock=True))


@catalog_admin_blueprint.post("/products/<int:product_id>/image/upload")
@roles_required("admin")
def product_image_upload(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None: return error("not_found", "Product not found.", 404)
    data = json_body()
    try: upload = create_product_image_upload(product.id, clean_text(data.get("filename"), 255), clean_text(data.get("content_type"), 100), int(data.get("size_bytes", 0)))
    except (StorageError, ValueError) as exc: return error("invalid_product_image", str(exc), 422)
    return jsonify(upload=upload), 201


@catalog_admin_blueprint.patch("/products/<int:product_id>/image")
@roles_required("admin")
def confirm_product_image(product_id: int):
    actor = get_current_user(); product = db.session.get(Product, product_id); image_url = clean_text(json_body().get("image_url"), 500)
    if product is None: return error("not_found", "Product not found.", 404)
    if not image_url.startswith("http"): return error("invalid_product_image", "A valid public image URL is required.", 422)
    product.image_url = image_url; audit(actor.id, "catalog.product_image_updated", "product", product.id); db.session.commit()
    return jsonify(product=product_payload(product, include_stock=True))


@catalog_admin_blueprint.delete("/products/<int:product_id>/image")
@roles_required("admin")
def remove_product_image(product_id: int):
    actor = get_current_user(); product = db.session.get(Product, product_id)
    if product is None: return error("not_found", "Product not found.", 404)
    product.image_url = None; audit(actor.id, "catalog.product_image_removed", "product", product.id); db.session.commit()
    return jsonify(product=product_payload(product, include_stock=True))


@catalog_admin_blueprint.patch("/variants/<int:variant_id>")
@roles_required("admin")
def update_variant(variant_id: int):
    actor = get_current_user()
    variant = db.session.get(ProductVariant, variant_id)
    if variant is None:
        return error("not_found", "Product variant not found.", 404)
    data = json_body()
    if "price_usd" in data:
        price = parse_decimal(data["price_usd"])
        if price is None:
            return error("invalid_price", "Price must be positive.", 422)
        variant.price_usd = price
    if "low_stock_threshold" in data:
        threshold = parse_decimal(data["low_stock_threshold"])
        if threshold is None:
            return error("invalid_threshold", "Threshold must be positive.", 422)
        variant.low_stock_threshold = threshold
    if "is_active" in data and isinstance(data["is_active"], bool):
        variant.is_active = data["is_active"]
    audit(actor.id, "catalog.variant_updated", "product_variant", variant.id)
    db.session.commit()
    return jsonify(product=product_payload(variant.product, include_stock=True))


@catalog_admin_blueprint.get("/inventory")
@roles_required("admin", "sales", "operator")
def inventory():
    rate = current_exchange_rate()
    products = db.session.scalars(db.select(Product).order_by(Product.line, Product.id)).all()
    return jsonify(products=[product_payload(product, include_stock=True, rate=rate) for product in products])


@catalog_admin_blueprint.post("/inventory/movements")
@roles_required("admin", "operator")
def create_inventory_movement():
    actor = get_current_user()
    data = json_body()
    variant = db.session.get(ProductVariant, data.get("variant_id"))
    location = db.session.get(InventoryLocation, data.get("location_id", 1))
    movement_type = clean_text(data.get("movement_type"), 32)
    quantity = parse_decimal(data.get("quantity"))
    reason = clean_text(data.get("reason"), 500)
    if variant is None or location is None or movement_type not in MOVEMENT_TYPES or quantity is None or not reason:
        return error("invalid_inventory_movement", "Variant, location, movement type, quantity and reason are required.", 422)
    if movement_type in {"outgoing", "waste"}:
        delta = -quantity
    elif movement_type == "adjustment":
        direction = clean_text(data.get("direction"), 8)
        if direction not in {"add", "subtract"}:
            return error("invalid_adjustment", "Adjustment direction must be add or subtract.", 422)
        delta = quantity if direction == "add" else -quantity
    else:
        delta = quantity
    balance = db.session.scalar(
        db.select(InventoryBalance).where(InventoryBalance.variant_id == variant.id, InventoryBalance.location_id == location.id).with_for_update()
    )
    if balance is None:
        balance = InventoryBalance(variant_id=variant.id, location_id=location.id, quantity=0)
        db.session.add(balance)
        db.session.flush()
    if Decimal(balance.quantity) + delta < 0:
        return error("insufficient_stock", "The movement would create negative inventory.", 422)
    balance.quantity = Decimal(balance.quantity) + delta
    movement = InventoryMovement(variant_id=variant.id, location_id=location.id, movement_type=movement_type, quantity_delta=delta, reason=reason, actor_user_id=actor.id)
    db.session.add(movement)
    db.session.flush()
    audit(actor.id, "inventory.movement_created", "inventory_movement", movement.id, {"variant_id": variant.id, "quantity_delta": str(delta)})
    db.session.commit()
    return jsonify(variant_id=variant.id, stock=str(variant_stock(variant.id))), 201


@catalog_admin_blueprint.get("/inventory/movements")
@roles_required("admin", "sales", "operator")
def list_inventory_movements():
    movements = db.session.scalars(db.select(InventoryMovement).order_by(InventoryMovement.id.desc()).limit(200)).all()
    return jsonify(movements=[{"id": item.id, "variant": item.variant.sku, "movement_type": item.movement_type, "quantity_delta": str(item.quantity_delta), "reason": item.reason, "created_at": item.created_at.isoformat()} for item in movements])


@catalog_admin_blueprint.get("/exchange-rates")
@roles_required("admin")
def list_exchange_rates():
    rates = db.session.scalars(db.select(ExchangeRate).order_by(ExchangeRate.effective_date.desc()).limit(90)).all()
    return jsonify(exchange_rates=[rate_payload(rate) | {"id": rate.id, "source_method": rate.source_method, "note": rate.note} for rate in rates])


@catalog_admin_blueprint.post("/exchange-rates")
@roles_required("admin")
def create_manual_exchange_rate():
    actor = get_current_user()
    data = json_body()
    rate = parse_decimal(data.get("rate_ves"))
    raw_date = clean_text(data.get("effective_date"), 10)
    note = clean_text(data.get("note"), 500)
    if rate is None or not note:
        return error("invalid_exchange_rate", "A positive rate and correction reason are required.", 422)
    try:
        effective_date = date.fromisoformat(raw_date)
    except ValueError:
        return error("invalid_exchange_rate_date", "Effective date must use YYYY-MM-DD.", 422)
    saved = save_exchange_rate(rate, effective_date, "manual://administration", "manual", note, actor.id)
    audit(actor.id, "exchange_rate.manually_saved", "exchange_rate", saved.id)
    db.session.commit()
    return jsonify(exchange_rate=rate_payload(saved)), 201


@catalog_admin_blueprint.post("/exchange-rates/sync")
@roles_required("admin")
def sync_exchange_rate():
    actor = get_current_user()
    try:
        saved = sync_official_bcv_rate()
    except (BcvRateError, OSError, requests.RequestException) as exc:
        return error("bcv_sync_failed", str(exc), 502)
    audit(actor.id, "exchange_rate.synchronized", "exchange_rate", saved.id)
    db.session.commit()
    return jsonify(exchange_rate=rate_payload(saved))
