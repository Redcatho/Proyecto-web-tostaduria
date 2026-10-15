from flask import Flask, jsonify

from flask_jwt_extended import get_jwt, get_jwt_identity

from app.api.auth.routes import auth_blueprint
from app.api.businesses.routes import businesses_blueprint
from app.api.admin.routes import admin_blueprint
from app.api.admin.catalog_routes import catalog_admin_blueprint
from app.api.catalog.routes import catalog_blueprint
from app.api.commerce.routes import commerce_blueprint
from app.api.credit.routes import credit_blueprint
from app.api.health.routes import health_blueprint
from app.api.operations.routes import operations_blueprint
from app.commands import register_commands
from app.config import Config
from app.extensions import db, jwt, limiter
from app.models import RevokedToken, User
from app.security import ensure_roles


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    Config.validate(app.config)
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    _configure_cors(app)
    _configure_security_headers(app)
    _register_error_handlers(app)
    app.register_blueprint(health_blueprint, url_prefix="/api")
    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")
    app.register_blueprint(businesses_blueprint, url_prefix="/api/businesses")
    app.register_blueprint(credit_blueprint, url_prefix="/api/credit-applications")
    app.register_blueprint(admin_blueprint, url_prefix="/api/admin")
    app.register_blueprint(catalog_admin_blueprint, url_prefix="/api/admin")
    app.register_blueprint(catalog_blueprint, url_prefix="/api/catalog")
    app.register_blueprint(commerce_blueprint, url_prefix="/api")
    app.register_blueprint(operations_blueprint, url_prefix="/api/operations")
    _configure_jwt(app)
    register_commands(app)
    from app.api.common import register_company_routes
    register_company_routes(app)

    with app.app_context():
        try:
            ensure_roles()
        except Exception:
            db.session.rollback()
            app.logger.warning("Roles could not be initialized during startup.")

    return app


def _configure_cors(app: Flask) -> None:
    from flask_cors import CORS

    origins = [origin.strip() for origin in app.config["CORS_ORIGINS"].split(",") if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)


def _configure_jwt(app: Flask) -> None:
    @jwt.user_lookup_loader
    def load_user(_jwt_header, jwt_data):
        return db.session.get(User, int(jwt_data["sub"]))

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_data):
        return db.session.scalar(db.select(RevokedToken).where(RevokedToken.jti == jwt_data["jti"])) is not None

    @jwt.unauthorized_loader
    def missing_token(message):
        return jsonify(error={"code": "authentication_required", "message": message}), 401

    @jwt.invalid_token_loader
    def invalid_token(message):
        return jsonify(error={"code": "invalid_session", "message": message}), 401

    @jwt.revoked_token_loader
    def revoked_token(_jwt_header, _jwt_payload):
        return jsonify(error={"code": "session_revoked", "message": "Session is no longer active."}), 401


def _configure_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; form-action 'self'"
        if app.config.get("ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(error={"code": "not_found", "message": "Resource not found."}), 404

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify(error={"code": "payload_too_large", "message": "Request payload is too large."}), 413

