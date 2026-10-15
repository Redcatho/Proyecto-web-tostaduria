from app.extensions import db
from app.models import Business, CreditApplication, CreditTerms, Role, User
from app.security import get_role, hash_password


def csrf_headers(client):
    cookie = client.get_cookie("csrf_access_token")
    return {"X-CSRF-TOKEN": cookie.value}


def register_customer(client, email="cliente@example.com"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Cliente Prueba", "password": "password-segura-123"},
    )


def login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_customer_registration_and_business_credit_request(client):
    response = register_customer(client)
    assert response.status_code == 201
    assert response.json["user"]["roles"] == ["customer"]

    profile = client.patch(
        "/api/businesses/me",
        json={
            "legal_name": "Cafe Prueba",
            "tax_id": "J-12345678-9",
            "business_type": "cafeteria",
            "contact_name": "Cliente Prueba",
            "contact_email": "cliente@example.com",
            "contact_phone": "04121234567",
        },
        headers=csrf_headers(client),
    )
    assert profile.status_code == 200
    assert profile.json["business"]["profile_status"] == "incomplete"

    address = client.post(
        "/api/businesses/me/addresses",
        json={"line1": "Av. Principal", "city": "Caracas", "state": "Distrito Capital"},
        headers=csrf_headers(client),
    )
    assert address.status_code == 201

    application = client.post(
        "/api/credit-applications",
        json={"requested_days": 15, "requested_limit_usd": "500", "justification": "Compra recurrente"},
        headers=csrf_headers(client),
    )
    assert application.status_code == 201
    assert application.json["application"]["status"] == "pending"


def test_admin_can_create_staff_and_review_credit(client, app):
    with app.app_context():
        admin = User(
            email="admin@example.com",
            full_name="Administrador",
            password_hash=hash_password("password-segura-123"),
            roles=[get_role("admin")],
        )
        db.session.add(admin)
        db.session.commit()

    assert login(client, "admin@example.com", "password-segura-123").status_code == 200
    staff = client.post(
        "/api/admin/users",
        json={
            "email": "operador@example.com",
            "full_name": "Operador Planta",
            "password": "password-segura-456",
            "role": "operator",
        },
        headers=csrf_headers(client),
    )
    assert staff.status_code == 201
    assert staff.json["user"]["roles"] == ["operator"]


def test_customer_cannot_access_admin_routes(client):
    assert register_customer(client).status_code == 201
    response = client.get("/api/admin/users")
    assert response.status_code == 403
    assert response.json["error"]["code"] == "forbidden"


def test_admin_can_approve_credit_application(client, app):
    with app.app_context():
        admin = User(email="admin@example.com", full_name="Administrador", password_hash=hash_password("password-segura-123"), roles=[get_role("admin")])
        business = Business(legal_name="Cafe Credito", tax_id="J-99999999-9", profile_status="complete")
        db.session.add_all([admin, business])
        db.session.flush()
        application = CreditApplication(business_id=business.id, requested_days=15, requested_limit_usd="1200")
        db.session.add(application)
        db.session.commit()
        application_id = application.id
        business_id = business.id

    assert login(client, "admin@example.com", "password-segura-123").status_code == 200
    response = client.patch(
        f"/api/admin/credit-applications/{application_id}",
        json={"decision": "approved", "payment_days": 30, "credit_limit_usd": "1000"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    with app.app_context():
        terms = db.session.scalar(db.select(CreditTerms).where(CreditTerms.business_id == business_id))
        assert terms.payment_days == 30
        assert str(terms.credit_limit_usd) == "1000.00"


def test_initial_admin_command_creates_two_administrators(app, monkeypatch):
    monkeypatch.setenv("ADMIN_1_EMAIL", "admin1@example.com")
    monkeypatch.setenv("ADMIN_1_PASSWORD", "password-segura-123")
    monkeypatch.setenv("ADMIN_2_EMAIL", "admin2@example.com")
    monkeypatch.setenv("ADMIN_2_PASSWORD", "password-segura-456")

    result = app.test_cli_runner().invoke(args=["create-initial-admins"])
    assert result.exit_code == 0
    with app.app_context():
        administrators = db.session.scalars(db.select(User).join(User.roles).where(Role.code == "admin")).all()
        assert len(administrators) == 2
