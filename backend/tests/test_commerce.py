from datetime import date

from app.extensions import db
from app.models import ExchangeRate, InventoryBalance, InventoryLocation, Product, ProductVariant, User
from app.security import get_role, hash_password


def csrf_headers(client):
    return {"X-CSRF-TOKEN": client.get_cookie("csrf_access_token").value}


def test_cart_quote_and_order_do_not_reserve_inventory(client, app):
    registration = client.post("/api/auth/register", json={"email": "comprador@example.com", "full_name": "Comprador", "password": "password-segura-123"})
    assert registration.status_code == 201
    headers = csrf_headers(client)
    profile = client.patch("/api/businesses/me", json={"legal_name": "Café Cliente", "tax_id": "J-55555555-5", "business_type": "cafeteria", "contact_name": "Comprador", "contact_email": "comprador@example.com", "contact_phone": "04121234567"}, headers=headers)
    assert profile.status_code == 200
    assert client.post("/api/businesses/me/addresses", json={"line1": "Av. Principal", "city": "Caracas", "state": "Distrito Capital"}, headers=headers).status_code == 201

    with app.app_context():
        product = Product(slug="carrito-comercial", line="commercial", name="Bulto comercial")
        variant = ProductVariant(product=product, sku="CART-BUNDLE", name="Bulto", sale_unit="bulto", inventory_unit="bulto", unit_weight_kg=8, packages_per_unit=40, price_usd=180, low_stock_threshold=1)
        location = InventoryLocation(name="Almacén principal")
        db.session.add_all([product, variant, location, ExchangeRate(currency="USD", rate_ves="50.00", effective_date=date(2026, 10, 12), source_url="test", source_method="manual")])
        db.session.flush(); db.session.add(InventoryBalance(variant_id=variant.id, location_id=location.id, quantity=10)); db.session.commit()
        variant_id = variant.id; address_id = 1

    added = client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": "2"}, headers=headers)
    assert added.status_code == 201
    quote = client.post("/api/quotes", json={"delivery_method": "pickup", "payment_condition": "advance_50"}, headers=headers)
    assert quote.status_code == 201
    assert quote.json["quote"]["total_usd"] == "360.00"
    assert quote.json["quote"]["required_advance_usd"] == "180.00"
    accepted = client.post(f"/api/quotes/{quote.json['quote']['id']}/accept", headers=headers)
    assert accepted.status_code == 201
    with app.app_context():
        balance = db.session.scalar(db.select(InventoryBalance).where(InventoryBalance.variant_id == variant_id))
        assert str(balance.quantity) == "10.000"


def test_verified_payment_confirms_order(client, app, monkeypatch):
    monkeypatch.setattr("app.api.commerce.routes.proof_exists", lambda _key: True)
    assert client.post("/api/auth/register", json={"email": "paying@example.com", "full_name": "Buyer", "password": "password-segura-123"}).status_code == 201
    headers = csrf_headers(client)
    assert client.patch("/api/businesses/me", json={"legal_name": "Pago Cafe", "tax_id": "J-44444444-4", "business_type": "cafeteria", "contact_name": "Buyer", "contact_email": "paying@example.com", "contact_phone": "04121234567"}, headers=headers).status_code == 200
    assert client.post("/api/businesses/me/addresses", json={"line1": "Av. Pago", "city": "Caracas", "state": "Distrito Capital"}, headers=headers).status_code == 201
    with app.app_context():
        product = Product(slug="pago-cafe", line="commercial", name="Pago café")
        variant = ProductVariant(product=product, sku="PAY-1", name="Bulto", sale_unit="bulto", inventory_unit="bulto", unit_weight_kg=8, price_usd=100, low_stock_threshold=1)
        location = InventoryLocation(name="Pago almacén")
        admin = User(email="payments-admin@example.com", full_name="Payments Admin", password_hash=hash_password("password-segura-123"), roles=[get_role("admin")])
        db.session.add_all([product, variant, location, admin, ExchangeRate(currency="USD", rate_ves="50", effective_date=date(2026, 10, 12), source_url="test", source_method="manual")]); db.session.flush()
        db.session.add(InventoryBalance(variant_id=variant.id, location_id=location.id, quantity=10)); db.session.commit(); variant_id = variant.id
    assert client.post("/api/cart/items", json={"variant_id": variant_id, "quantity": "1"}, headers=headers).status_code == 201
    quote = client.post("/api/quotes", json={"delivery_method": "pickup", "payment_condition": "full_payment"}, headers=headers).json["quote"]
    quote_pdf = client.get(f"/api/quotes/{quote['id']}/pdf")
    assert quote_pdf.status_code == 200
    assert quote_pdf.mimetype == "application/pdf"
    order = client.post(f"/api/quotes/{quote['id']}/accept", headers=headers).json["order"]
    payment = client.post(f"/api/orders/{order['id']}/payment-submissions", json={"currency": "USD", "amount": "100", "reference": "ABC123", "payment_method": "transfer", "proof_storage_key": "payment-proofs/1/proof.pdf", "proof_original_filename": "proof.pdf", "proof_content_type": "application/pdf", "proof_size_bytes": 100}, headers=headers)
    assert payment.status_code == 201
    admin_client = app.test_client(); assert admin_client.post("/api/auth/login", json={"email": "payments-admin@example.com", "password": "password-segura-123"}).status_code == 200
    result = admin_client.patch(f"/api/admin/payment-submissions/{payment.json['payment']['id']}", json={"decision": "verified"}, headers=csrf_headers(admin_client))
    assert result.status_code == 200
    assert result.json["order"]["status"] == "confirmed"
    assert result.json["order"]["outstanding_usd"] == "0"
    order_pdf = client.get(f"/api/orders/{order['id']}/pdf")
    assert order_pdf.status_code == 200
    assert order_pdf.mimetype == "application/pdf"
    started = admin_client.patch(f"/api/operations/orders/{order['id']}/production/start", headers=csrf_headers(admin_client))
    assert started.status_code == 200
    assert started.json["order"]["status"] == "in_production"
    with app.app_context():
        balance = db.session.scalar(db.select(InventoryBalance).where(InventoryBalance.variant_id == variant_id))
        assert str(balance.quantity) == "9.000"
    ready = admin_client.patch(f"/api/operations/orders/{order['id']}/production/complete", headers=csrf_headers(admin_client))
    assert ready.json["order"]["status"] == "ready"
    dispatched = admin_client.post(f"/api/operations/orders/{order['id']}/dispatch", json={"carrier_name": "Mensajería Café", "tracking_number": "TRACK-1"}, headers=csrf_headers(admin_client))
    assert dispatched.status_code == 201
    delivered = admin_client.patch(f"/api/operations/orders/{order['id']}/deliver", headers=csrf_headers(admin_client))
    assert delivered.json["order"]["status"] == "delivered"
    returned = admin_client.post(f"/api/operations/orders/{order['id']}/return", json={"reason": "Cliente devolvió el bulto"}, headers=csrf_headers(admin_client))
    assert returned.json["order"]["status"] == "returned"
    with app.app_context():
        balance = db.session.scalar(db.select(InventoryBalance).where(InventoryBalance.variant_id == variant_id))
        assert str(balance.quantity) == "10.000"
