from datetime import UTC, datetime
from decimal import Decimal

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_current_user, jwt_required

from app.api.businesses.routes import current_business
from app.api.common import clean_text, error, json_body, parse_decimal
from app.extensions import db
from app.models import BusinessAddress, CartItem, CreditTerms, CreditUsage, Order, OrderItem, OrderStatusHistory, PaymentSubmission, ProductVariant, Quote, QuoteItem
from app.security import audit
from app.services.commerce import DELIVERY_METHODS, CommerceValidationError, cart_summary, get_cart, quote_expiration, required_advance, validate_cart
from app.services.orders import credit_available, order_payload
from app.services.storage import StorageError, proof_exists, read_url, save_proof_file
from app.services.documents import render_pdf
from app.services.notifications import notify_order

commerce_blueprint = Blueprint("commerce", __name__)


def quote_payload(quote: Quote) -> dict:
    return {"id": quote.id, "number": quote.number, "status": quote.status, "delivery_method": quote.delivery_method, "payment_condition": quote.payment_condition, "subtotal_usd": str(quote.subtotal_usd), "discount_usd": str(quote.discount_usd), "total_usd": str(quote.total_usd), "total_ves": str(quote.total_ves), "rate_ves": str(quote.rate_ves), "rate_effective_date": quote.rate_effective_date.isoformat(), "required_advance_usd": str(quote.required_advance_usd), "estimated_dispatch_hours": quote.estimated_dispatch_hours, "estimate_note": quote.estimate_note, "issued_at": quote.issued_at.isoformat(), "expires_at": quote.expires_at.isoformat(), "items": [{"sku": item.sku_snapshot, "product_name": item.product_name_snapshot, "quantity": str(item.quantity), "roast_profile": item.roast_profile, "unit_price_usd": str(item.unit_price_usd), "discount_per_unit_usd": str(item.discount_per_unit_usd), "line_total_usd": str(item.line_total_usd)} for item in quote.items]}


@commerce_blueprint.get("/cart")
@jwt_required()
def read_cart():
    return jsonify(cart=cart_summary(get_cart(get_current_user().id)))


@commerce_blueprint.get("/cart/count")
@jwt_required()
def cart_count():
    cart = get_cart(get_current_user().id, create=False)
    return jsonify(count=len(cart.items) if cart else 0)


@commerce_blueprint.post("/cart/items")
@jwt_required()
def add_cart_item():
    user = get_current_user(); data = json_body(); cart = get_cart(user.id)
    variant = db.session.get(ProductVariant, data.get("variant_id")); quantity = parse_decimal(data.get("quantity"))
    if variant is None or quantity is None:
        return error("invalid_cart_item", "A product variant and positive quantity are required.", 422)
    roast_profile = clean_text(data.get("roast_profile"), 24) or None
    existing = db.session.scalar(db.select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant.id, CartItem.roast_profile == roast_profile))
    if existing:
        existing.quantity = Decimal(existing.quantity) + quantity
        existing.customer_note = clean_text(data.get("customer_note"), 1000) or existing.customer_note
    else:
        db.session.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=quantity, roast_profile=roast_profile, customer_note=clean_text(data.get("customer_note"), 1000) or None))
    db.session.commit()
    return jsonify(cart=cart_summary(cart)), 201


@commerce_blueprint.patch("/cart/items/<int:item_id>")
@jwt_required()
def update_cart_item(item_id: int):
    cart = get_cart(get_current_user().id); item = db.session.get(CartItem, item_id); data = json_body()
    if item is None or item.cart_id != cart.id:
        return error("not_found", "Cart item not found.", 404)
    quantity = parse_decimal(data.get("quantity"))
    if quantity is None: return error("invalid_quantity", "Quantity must be positive.", 422)
    item.quantity = quantity; item.customer_note = clean_text(data.get("customer_note"), 1000) or None
    db.session.commit(); return jsonify(cart=cart_summary(cart))


@commerce_blueprint.delete("/cart/items/<int:item_id>")
@jwt_required()
def delete_cart_item(item_id: int):
    cart = get_cart(get_current_user().id); item = db.session.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id: return error("not_found", "Cart item not found.", 404)
    db.session.delete(item); db.session.commit(); return jsonify(cart=cart_summary(cart))


@commerce_blueprint.post("/cart/validate")
@jwt_required()
def check_cart():
    try: return jsonify(cart=validate_cart(get_cart(get_current_user().id)))
    except CommerceValidationError as exc: return error("cart_validation_failed", str(exc), 422)


@commerce_blueprint.post("/quotes")
@jwt_required()
def issue_quote():
    user = get_current_user(); business = current_business(user); data = json_body()
    if business is None or business.profile_status != "complete": return error("complete_business_required", "Complete the business profile before requesting a quote.", 422)
    delivery_method = clean_text(data.get("delivery_method"), 24); payment_condition = clean_text(data.get("payment_condition"), 32)
    address_id = data.get("delivery_address_id")
    if delivery_method not in DELIVERY_METHODS: return error("invalid_delivery_method", "Choose a valid delivery method.", 422)
    if delivery_method != "pickup":
        address = db.session.get(BusinessAddress, address_id)
        if address is None or address.business_id != business.id: return error("invalid_delivery_address", "Choose a business delivery address.", 422)
    try: summary = validate_cart(get_cart(user.id)); advance = required_advance(Decimal(summary["total_usd"]), payment_condition, business.id)
    except CommerceValidationError as exc: return error("quote_validation_failed", str(exc), 422)
    rate = summary["exchange_rate"]; number = f"COT-{datetime.now(UTC):%Y%m%d}-{user.id:04d}-{int(datetime.now(UTC).timestamp()) % 10000:04d}"
    quote = Quote(number=number, business_id=business.id, created_by_user_id=user.id, delivery_method=delivery_method, delivery_address_id=address_id if delivery_method != "pickup" else None, payment_condition=payment_condition, rate_ves=rate["rate_ves"], rate_effective_date=datetime.fromisoformat(rate["effective_date"]).date(), subtotal_usd=summary["subtotal_usd"], discount_usd=summary["discount_usd"], total_usd=summary["total_usd"], total_ves=summary["total_ves"], required_advance_usd=advance, estimated_dispatch_hours=summary["estimated_dispatch_hours"], estimate_note=summary["estimate_note"], expires_at=quote_expiration())
    db.session.add(quote); db.session.flush()
    for item in get_cart(user.id).items:
        variant = item.variant; discount = Decimal(summary["discount_per_kg"]) if variant.product.line == "cafeteria" else Decimal("0")
        db.session.add(QuoteItem(quote_id=quote.id, variant_id=variant.id, sku_snapshot=variant.sku, product_name_snapshot=variant.product.name, line_snapshot=variant.product.line, quantity=item.quantity, roast_profile=item.roast_profile, customer_note=item.customer_note, unit_price_usd=variant.price_usd, discount_per_unit_usd=discount, line_total_usd=(Decimal(variant.price_usd) - discount) * Decimal(item.quantity)))
    audit(user.id, "quote.issued", "quote", quote.id); db.session.commit(); return jsonify(quote=quote_payload(quote)), 201


@commerce_blueprint.get("/quotes")
@jwt_required()
def list_quotes():
    business = current_business(get_current_user());
    if business is None: return jsonify(quotes=[])
    quotes = db.session.scalars(db.select(Quote).where(Quote.business_id == business.id).order_by(Quote.id.desc())).all(); return jsonify(quotes=[quote_payload(item) for item in quotes])


@commerce_blueprint.get("/orders")
@jwt_required()
def list_orders():
    business = current_business(get_current_user())
    if business is None: return jsonify(orders=[])
    orders = db.session.scalars(db.select(Order).where(Order.business_id == business.id).order_by(Order.id.desc())).all()
    return jsonify(orders=[order_payload(order, include_payments=False) for order in orders])


@commerce_blueprint.get("/orders/<int:order_id>")
@jwt_required()
def get_order(order_id: int):
    business = current_business(get_current_user()); order = db.session.get(Order, order_id)
    if order is None or business is None or order.business_id != business.id: return error("not_found", "Order not found.", 404)
    return jsonify(order=order_payload(order))


@commerce_blueprint.post("/orders/<int:order_id>/payment-proofs/upload")
@jwt_required()
def create_payment_proof_upload(order_id: int):
    user = get_current_user(); business = current_business(user); order = db.session.get(Order, order_id)
    if order is None or business is None or order.business_id != business.id or order.status in {"cancelled", "confirmed"}: return error("payment_not_allowed", "A payment proof cannot be added to this order.", 422)
    file = request.files.get("file")
    if file is None or not file.filename: return error("invalid_payment_proof", "A file is required.", 422)
    content_type = file.content_type or "application/octet-stream"
    file.seek(0, 2); size_bytes = file.tell(); file.seek(0)
    if size_bytes < 1: return error("invalid_payment_proof", "File is empty.", 422)
    try: upload = save_proof_file(file.read(), user.id, file.filename, content_type, size_bytes)
    except (StorageError, ValueError): return error("invalid_payment_proof", "The payment proof cannot be uploaded.", 422)
    return jsonify(upload=upload), 201


@commerce_blueprint.post("/orders/<int:order_id>/payment-submissions")
@jwt_required()
def submit_payment(order_id: int):
    user = get_current_user(); business = current_business(user); order = db.session.get(Order, order_id); data = json_body()
    if order is None or business is None or order.business_id != business.id or order.status in {"cancelled", "confirmed"}: return error("payment_not_allowed", "A payment cannot be submitted for this order.", 422)
    amount = parse_decimal(data.get("amount")); currency = clean_text(data.get("currency"), 8).upper(); key = clean_text(data.get("proof_storage_key"), 512)
    if amount is None or currency not in {"USD", "VES"} or not key.startswith(f"payment-proofs/{user.id}/") or not proof_exists(key): return error("invalid_payment_submission", "Amount, currency and uploaded payment proof are required.", 422)
    equivalent = amount if currency == "USD" else (amount / Decimal(order.rate_ves)).quantize(Decimal("0.01"))
    payment = PaymentSubmission(order_id=order.id, submitted_by_user_id=user.id, currency=currency, amount=amount, amount_usd_equivalent=equivalent, reference=clean_text(data.get("reference"), 120), payment_method=clean_text(data.get("payment_method"), 40), proof_storage_key=key, proof_original_filename=clean_text(data.get("proof_original_filename"), 255), proof_content_type=clean_text(data.get("proof_content_type"), 100), proof_size_bytes=int(data.get("proof_size_bytes", 0)), note=clean_text(data.get("note"), 1000) or None)
    if not payment.reference or not payment.payment_method or not payment.proof_original_filename or payment.proof_size_bytes < 1: return error("invalid_payment_submission", "Payment reference and proof metadata are required.", 422)
    db.session.add(payment)
    if order.status == "pending_payment": order.status = "payment_under_review"; db.session.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Payment proof submitted.", actor_user_id=user.id))
    audit(user.id, "payment.submitted", "payment_submission", payment.id, {"order_id": order.id}); db.session.commit()
    notify_order(order, "payment_review")
    return jsonify(payment={"id": payment.id, "status": payment.status}), 201


@commerce_blueprint.get("/orders/<int:order_id>/payment-submissions/<int:payment_id>/proof")
@jwt_required()
def customer_payment_proof_url(order_id: int, payment_id: int):
    business = current_business(get_current_user()); order = db.session.get(Order, order_id); payment = db.session.get(PaymentSubmission, payment_id)
    if order is None or payment is None or payment.order_id != order.id or business is None or order.business_id != business.id: return error("not_found", "Payment proof not found.", 404)
    try: return jsonify(url=read_url(payment.proof_storage_key))
    except StorageError: return error("storage_unavailable", "Payment proof storage is unavailable.", 503)


@commerce_blueprint.get("/quotes/<int:quote_id>")
@jwt_required()
def get_quote(quote_id: int):
    business = current_business(get_current_user()); quote = db.session.get(Quote, quote_id)
    if quote is None or business is None or quote.business_id != business.id: return error("not_found", "Quote not found.", 404)
    return jsonify(quote=quote_payload(quote))


@commerce_blueprint.get("/quotes/<int:quote_id>/pdf")
@jwt_required()
def quote_pdf(quote_id: int):
    business = current_business(get_current_user()); quote = db.session.get(Quote, quote_id)
    if quote is None or business is None or quote.business_id != business.id: return error("not_found", "Quote not found.", 404)
    try: content = render_pdf("Cotización", quote.number, business.legal_name, quote.items, quote.total_usd, quote.payment_condition)
    except RuntimeError as exc: return error("pdf_unavailable", str(exc), 503)
    return Response(content, mimetype="application/pdf", headers={"Content-Disposition": f'attachment; filename="{quote.number}.pdf"'})


@commerce_blueprint.get("/orders/<int:order_id>/pdf")
@jwt_required()
def order_pdf(order_id: int):
    business = current_business(get_current_user()); order = db.session.get(Order, order_id)
    if order is None or business is None or order.business_id != business.id: return error("not_found", "Order not found.", 404)
    try: content = render_pdf("Pedido", order.number, business.legal_name, order.items, order.total_usd, order.payment_condition or "—")
    except RuntimeError as exc: return error("pdf_unavailable", str(exc), 503)
    return Response(content, mimetype="application/pdf", headers={"Content-Disposition": f'attachment; filename="{order.number}.pdf"'})


@commerce_blueprint.post("/quotes/<int:quote_id>/accept")
@jwt_required()
def accept_quote(quote_id: int):
    user = get_current_user(); business = current_business(user); quote = db.session.get(Quote, quote_id)
    if quote is None or business is None or quote.business_id != business.id: return error("not_found", "Quote not found.", 404)
    expires_at = quote.expires_at if quote.expires_at.tzinfo else quote.expires_at.replace(tzinfo=UTC)
    if quote.status != "issued" or expires_at < datetime.now(UTC):
        if quote.status == "issued": quote.status = "expired"; db.session.commit()
        return error("quote_expired", "This quote has expired.", 422)
    status = "pending_payment"; required_payment = quote.required_advance_usd if quote.payment_condition == "advance_50" else quote.total_usd
    order = Order(number=quote.number.replace("COT", "PED", 1), quote_id=quote.id, business_id=business.id, status=status, payment_condition=quote.payment_condition, total_usd=quote.total_usd, total_ves=quote.total_ves, rate_ves=quote.rate_ves, rate_effective_date=quote.rate_effective_date, required_payment_usd=required_payment, estimated_dispatch_hours=quote.estimated_dispatch_hours, estimate_note=quote.estimate_note); db.session.add(order); db.session.flush()
    if quote.payment_condition == "credit":
        terms = db.session.scalar(db.select(CreditTerms).where(CreditTerms.business_id == business.id, CreditTerms.is_active.is_(True)).order_by(CreditTerms.id.desc()))
        if terms is None or credit_available(business.id, terms) < Decimal(quote.total_usd):
            db.session.rollback(); return error("credit_unavailable", "There is no sufficient active credit for this order.", 422)
        db.session.add(CreditUsage(business_id=business.id, order_id=order.id, credit_terms_id=terms.id, amount_usd=quote.total_usd, status="active")); order.status = "confirmed"; order.confirmed_at = datetime.now(UTC); db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed", note="Credit terms applied.", actor_user_id=user.id))
    for item in quote.items: db.session.add(OrderItem(order_id=order.id, quote_item_id=item.id, sku_snapshot=item.sku_snapshot, product_name_snapshot=item.product_name_snapshot, quantity=item.quantity, roast_profile=item.roast_profile, customer_note=item.customer_note, unit_price_usd=item.unit_price_usd, discount_per_unit_usd=item.discount_per_unit_usd, line_total_usd=item.line_total_usd))
    db.session.add(OrderStatusHistory(order_id=order.id, status=order.status, note="Order created from accepted quote.", actor_user_id=user.id)); quote.status = "accepted"; audit(user.id, "quote.accepted", "quote", quote.id, {"order_id": order.id}); db.session.commit(); notify_order(order, "created"); return jsonify(order={"id": order.id, "number": order.number, "status": order.status}), 201
