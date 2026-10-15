from datetime import UTC, datetime
from functools import wraps

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import jsonify
from flask_jwt_extended import get_current_user, get_jwt, jwt_required

from app.extensions import db
from app.models import AuditLog, RevokedToken, Role

password_hasher = PasswordHasher()

ROLE_DEFINITIONS = {
    "customer": "Cliente",
    "admin": "Administracion",
    "operator": "Operador de planta",
    "sales": "Ventas",
    "dispatch": "Despacho",
}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def ensure_roles() -> None:
    existing = {role.code for role in db.session.scalars(db.select(Role)).all()}
    for code, name in ROLE_DEFINITIONS.items():
        if code not in existing:
            db.session.add(Role(code=code, name=name))
    db.session.commit()


def get_role(code: str) -> Role:
    role = db.session.scalar(db.select(Role).where(Role.code == code))
    if role is None:
        ensure_roles()
        role = db.session.scalar(db.select(Role).where(Role.code == code))
    if role is None:
        raise RuntimeError(f"Role '{code}' could not be initialized")
    return role


def roles_required(*allowed_roles: str):
    def decorator(view):
        @wraps(view)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None or not user.is_active:
                return jsonify(error={"code": "account_inactive", "message": "Account is not active."}), 403
            if not user.has_role(*allowed_roles):
                return jsonify(error={"code": "forbidden", "message": "Insufficient permissions."}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def revoke_current_token() -> None:
    claims = get_jwt()
    expires_at = datetime.fromtimestamp(claims["exp"], UTC)
    db.session.add(RevokedToken(jti=claims["jti"], expires_at=expires_at))


def audit(actor_user_id: int | None, action: str, entity_type: str, entity_id: int | str, details: dict | None = None) -> None:
    db.session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details,
        )
    )
