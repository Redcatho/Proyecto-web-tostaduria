from app.extensions import db
from app.models import InventoryLocation, Product, ProductVariant, User
from app.security import get_role, hash_password


def login_admin(client, app):
    with app.app_context():
        admin = User(email="catalog-admin@example.com", full_name="Admin Catalogo", password_hash=hash_password("password-segura-123"), roles=[get_role("admin")])
        db.session.add(admin)
        db.session.commit()
    response = client.post("/api/auth/login", json={"email": "catalog-admin@example.com", "password": "password-segura-123"})
    assert response.status_code == 200
    return {"X-CSRF-TOKEN": client.get_cookie("csrf_access_token").value}


def create_product_data(app):
    with app.app_context():
        product = Product(slug="catalogo-prueba", line="commercial", name="Café de prueba", description="Descripción temporal")
        variant = ProductVariant(product=product, sku="TEST-BULTO", name="Bulto prueba", sale_unit="bulto", inventory_unit="bulto", unit_weight_kg=8, packages_per_unit=40, price_usd=180, low_stock_threshold=3)
        location = InventoryLocation(name="Almacén principal")
        db.session.add_all([product, variant, location])
        db.session.commit()
        return product.slug, variant.id, location.id


def test_public_catalog_hides_exact_inventory_and_commercial_always_available(client, app):
    slug, _, _ = create_product_data(app)
    response = client.get("/api/catalog/products")
    assert response.status_code == 200
    product = next(item for item in response.json["products"] if item["slug"] == slug)
    assert "stock" not in product["variants"][0]
    assert product["variants"][0]["availability"] == "Disponible"


def test_inventory_movements_prevent_negative_stock(client, app):
    headers = login_admin(client, app)
    _, variant_id, location_id = create_product_data(app)
    incoming = client.post("/api/admin/inventory/movements", json={"variant_id": variant_id, "location_id": location_id, "movement_type": "incoming", "quantity": "10", "reason": "Ingreso inicial"}, headers=headers)
    assert incoming.status_code == 201
    assert incoming.json["stock"] == "10.000"

    invalid = client.post("/api/admin/inventory/movements", json={"variant_id": variant_id, "location_id": location_id, "movement_type": "outgoing", "quantity": "11", "reason": "Salida inválida"}, headers=headers)
    assert invalid.status_code == 422
    assert invalid.json["error"]["code"] == "insufficient_stock"


def test_admin_can_record_manual_bcv_rate(client, app):
    headers = login_admin(client, app)
    response = client.post("/api/admin/exchange-rates", json={"rate_ves": "50.25", "effective_date": "2026-10-12", "note": "Corrección autorizada"}, headers=headers)
    assert response.status_code == 201
    assert response.json["exchange_rate"]["rate_ves"] == "50.25"
    catalog_rate = client.get("/api/catalog/exchange-rates/current")
    assert catalog_rate.json["exchange_rate"]["effective_date"] == "2026-10-12"
