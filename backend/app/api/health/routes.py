from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.extensions import db

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/health")
def health_check():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        current_app.logger.exception("Database health check failed")
        return jsonify(status="unavailable", database="unavailable"), 503

    return jsonify(
        status="ok",
        database="ok",
        timestamp=datetime.now(UTC).isoformat(),
    )


@health_blueprint.get("/version")
def version():
    return jsonify(
        version=current_app.config["APP_VERSION"],
        environment=current_app.config["ENV"],
    )
