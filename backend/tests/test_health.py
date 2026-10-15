def test_health_check(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["database"] == "ok"


def test_version(client):
    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json["version"] == "0.1.0"


def test_provider_postgres_urls_use_psycopg_driver():
    from app.config import normalize_database_url

    assert normalize_database_url("postgres://user:pass@host/database") == "postgresql+psycopg://user:pass@host/database"
