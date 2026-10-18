import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, Response, current_app, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_jwt,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from app.api.common import clean_text, error, json_body, user_payload
from app.extensions import db, limiter
from app.models import PasswordResetToken, RefreshToken, RevokedToken, User
from app.security import audit, get_role, hash_password, revoke_current_token, verify_password

auth_blueprint = Blueprint("auth", __name__)


def _issue_session(response, user: User) -> str:
    roles = sorted(role.code for role in user.roles)
    access_token = create_access_token(identity=str(user.id), additional_claims={"roles": roles})
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims={"roles": roles})
    refresh_claims = decode_token(refresh_token)
    db.session.add(
        RefreshToken(
            jti=refresh_claims["jti"],
            user_id=user.id,
            expires_at=datetime.fromtimestamp(refresh_claims["exp"], UTC),
        )
    )
    db.session.commit()
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return access_token


@auth_blueprint.post("/register")
@limiter.limit("8 per hour")
def register():
    data = json_body()
    email = clean_text(data.get("email")).lower()
    full_name = clean_text(data.get("full_name"), 160)
    password = str(data.get("password") or "")

    if not email or "@" not in email or not full_name:
        return error("invalid_registration", "Name and a valid email are required.", 422)
    if len(password) < 6:
        return error("weak_password", "Password must contain at least 6 characters.", 422)
    if db.session.scalar(db.select(User).where(User.email == email)):
        return error("email_unavailable", "This email is already registered.", 409)

    user = User(
        email=email,
        full_name=full_name,
        phone=clean_text(data.get("phone"), 40) or None,
        password_hash=hash_password(password),
        roles=[get_role("customer")],
    )
    db.session.add(user)
    db.session.flush()
    audit(user.id, "user.registered", "user", user.id)
    db.session.commit()

    response = jsonify(user=user_payload(user))
    token = _issue_session(response, user)
    response.set_data(jsonify(user=user_payload(user), access_token=token).get_data())
    return response, 201


@auth_blueprint.post("/login")
@limiter.limit("10 per hour")
def login():
    data = json_body()
    email = clean_text(data.get("email")).lower()
    password = str(data.get("password") or "")
    user = db.session.scalar(db.select(User).where(User.email == email))

    if user is None or not verify_password(user.password_hash, password):
        return error("invalid_credentials", "Invalid email or password.", 401)
    if not user.is_active:
        return error("account_inactive", "This account is not active.", 403)

    user.last_login_at = datetime.now(UTC)
    audit(user.id, "user.logged_in", "user", user.id)
    db.session.commit()
    response = jsonify(user=user_payload(user))
    token = _issue_session(response, user)
    response.set_data(jsonify(user=user_payload(user), access_token=token).get_data())
    return response


@auth_blueprint.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user = get_current_user()
    claims = get_jwt()
    refresh_record = db.session.scalar(db.select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
    if user is None or not user.is_active or refresh_record is None or refresh_record.revoked_at is not None:
        return error("session_revoked", "Session is no longer active.", 401)

    refresh_record.revoked_at = datetime.now(UTC)
    revoke_current_token()
    response = jsonify(user=user_payload(user))
    token = _issue_session(response, user)
    response.set_data(jsonify(user=user_payload(user), access_token=token).get_data())
    next_refresh = db.session.scalar(
        db.select(RefreshToken).where(RefreshToken.user_id == user.id).order_by(RefreshToken.id.desc())
    )
    refresh_record.replaced_by_jti = next_refresh.jti if next_refresh else None
    db.session.commit()
    return response


@auth_blueprint.post("/logout")
@jwt_required(verify_type=False)
def logout():
    claims = get_jwt()
    revoke_current_token()
    if claims["type"] == "refresh":
        refresh_record = db.session.scalar(db.select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
        if refresh_record:
            refresh_record.revoked_at = datetime.now(UTC)
    db.session.commit()
    response = jsonify(message="Session closed.")
    unset_jwt_cookies(response)
    return response


@auth_blueprint.get("/me")
@jwt_required()
def current_account():
    user = get_current_user()
    if user is None or not user.is_active:
        return error("account_inactive", "This account is not active.", 403)
    return jsonify(user=user_payload(user))


@auth_blueprint.patch("/me")
@jwt_required()
def update_account():
    user = get_current_user()
    data = json_body()
    full_name = clean_text(data.get("full_name"), 160)
    if not full_name:
        return error("invalid_profile", "Full name is required.", 422)
    user.full_name = full_name
    user.phone = clean_text(data.get("phone"), 40) or None
    audit(user.id, "user.profile_updated", "user", user.id)
    db.session.commit()
    return jsonify(user=user_payload(user))


@auth_blueprint.patch("/me/password")
@jwt_required()
def change_password():
    user = get_current_user()
    data = json_body()
    current_password = str(data.get("current_password") or "")
    new_password = str(data.get("new_password") or "")
    if not verify_password(user.password_hash, current_password):
        return error("invalid_credentials", "Current password is invalid.", 401)
    if len(new_password) < 6:
        return error("weak_password", "Password must contain at least 6 characters.", 422)
    user.password_hash = hash_password(new_password)
    db.session.execute(db.update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked_at=datetime.now(UTC)))
    revoke_current_token()
    audit(user.id, "user.password_changed", "user", user.id)
    db.session.commit()
    response = jsonify(message="Password updated. Please sign in again.")
    unset_jwt_cookies(response)
    return response


@auth_blueprint.post("/password-reset/request")
@limiter.limit("5 per hour")
def request_password_reset():
    email = clean_text(json_body().get("email")).lower()
    user = db.session.scalar(db.select(User).where(User.email == email))
    reset_token = None
    if user and user.is_active:
        reset_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        db.session.add(
            PasswordResetToken(
                token_hash=token_hash,
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        audit(user.id, "user.password_reset_requested", "user", user.id)
        db.session.commit()

    payload = {"message": "If the account exists, password reset instructions will be sent."}
    if reset_token and current_app.config["ENV"] == "development":
        payload["development_token"] = reset_token
    return jsonify(payload)


@auth_blueprint.post("/password-reset/confirm")
@limiter.limit("5 per hour")
def confirm_password_reset():
    data = json_body()
    token = str(data.get("token") or "")
    new_password = str(data.get("new_password") or "")
    if len(new_password) < 6:
        return error("weak_password", "Password must contain at least 6 characters.", 422)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset_record = db.session.scalar(db.select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if reset_record is None or reset_record.used_at is not None or reset_record.expires_at < datetime.now(UTC):
        return error("invalid_reset_token", "Password reset token is invalid or expired.", 422)

    user = db.session.get(User, reset_record.user_id)
    user.password_hash = hash_password(new_password)
    reset_record.used_at = datetime.now(UTC)
    db.session.execute(db.update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked_at=datetime.now(UTC)))
    audit(user.id, "user.password_reset", "user", user.id)
    db.session.commit()
    return jsonify(message="Password updated. You can now sign in.")
