import sys
from pathlib import Path

import pytest

# Ensure the backend root is on sys.path so that "app" can be imported
_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from app import create_app
from app.extensions import db
from app.security import ensure_roles


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-with-at-least-thirty-two-characters",
            "JWT_SECRET_KEY": "test-secret-with-at-least-thirty-two-characters",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "CORS_ORIGINS": "http://localhost:5173",
        }
    )
    with app.app_context():
        db.create_all()
        ensure_roles()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
