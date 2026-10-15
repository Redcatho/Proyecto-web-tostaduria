from datetime import UTC, datetime

from flask import Blueprint, jsonify
from flask_jwt_extended import get_current_user

from app.api.common import business_payload, clean_text, credit_terms_payload, error, json_body, parse_decimal, user_payload
from app.api.credit.routes import VALID_DAYS, application_payload
from app.extensions import db
from app.models import Business, CreditApplication, CreditTerms, CreditUsage, Order, OrderStatusHistory, PaymentSubmission, User
from app.security import ROLE_DEFINITIONS, audit, get_role, hash_password, roles_required
from app.services.orders import confirm_if_paid, order_payload
from app.services.storage import StorageError, read_url
from app.services.notifications import notify_order

admin_blueprint = Blueprint("admin", __name__)
STAFF_ROLES = {"admin", "operator", "sales", "dispatch"}


@admin_blueprint.get("/users")
@roles_required("admin")
def list_users():
    users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
    return jsonify(users=[user_payload(user) for user in users])


@admin_blueprint.post("/users")
@roles_required("admin")
def create_staff_user():
    actor = get_current_user()
    data = json_body()
    email = clean_text(data.get("email")).lower()
    full_name = clean_text(data.get("full_name"), 160)
    password = str(data.get("password") or "")
    role_code = clean_text(data.get("role"), 32)
    if not email or "@" not in email or not full_name or role_code not in STAFF_ROLES:
        return error("invalid_staff_user", "Name, email and a valid staff role are required.", 422)
    if len(password) < 6:
        return error("weak_password", "Password must contain at least 6 characters.", 422)
    if db.session.scalar(db.select(User).where(User.email == email)):
        return error("email_unavailable", "This email is already registered.", 409)
    user = User(
        email=email,
        full_name=full_name,
        phone=clean_text(data.get("phone"), 40) or None,
        password_hash=hash_password(password),
        roles=[get_role(role_code)],
    )
    db.session.add(user)
    db.session.flush()
    audit(actor.id, "staff_user.created", "user", user.id, {"role": role_code})
    db.session.commit()
    return jsonify(user=user_payload(user)), 201


@admin_blueprint.patch("/users/<int:user_id>/status")
@roles_required("admin")
def set_user_status(user_id: int):
    actor = get_current_user()
    user = db.session.get(User, user_id)
    is_active = json_body().get("is_active")
    if user is None:
        return error("not_found", "User not found.", 404)
    if not isinstance(is_active, bool):
        return error("invalid_status", "is_active must be boolean.", 422)
    if user.id == actor.id and not is_active:
        return error("self_suspension", "You cannot suspend your own account.", 422)
    user.is_active = is_active
    audit(actor.id, "user.status_updated", "user", user.id, {"is_active": is_active})
    db.session.commit()
    return jsonify(user=user_payload(user))


@admin_blueprint.patch("/users/<int:user_id>/roles")
@roles_required("admin")
def set_user_roles(user_id: int):
    actor = get_current_user()
    user = db.session.get(User, user_id)
    role_codes = json_body().get("roles")
    if user is None:
        return error("not_found", "User not found.", 404)
    if not isinstance(role_codes, list) or not role_codes or any(code not in ROLE_DEFINITIONS for code in role_codes):
        return error("invalid_roles", "At least one valid role is required.", 422)
    if user.id == actor.id and "admin" not in role_codes:
        return error("self_role_change", "You cannot remove your own administrator role.", 422)
    user.roles = [get_role(code) for code in sorted(set(role_codes))]
    audit(actor.id, "user.roles_updated", "user", user.id, {"roles": role_codes})
    db.session.commit()
    return jsonify(user=user_payload(user))


@admin_blueprint.get("/businesses")
@roles_required("admin", "sales")
def list_businesses():
    businesses = db.session.scalars(db.select(Business).order_by(Business.created_at.desc())).all()
    return jsonify(businesses=[business_payload(business) for business in businesses])


@admin_blueprint.get("/credit-applications")
@roles_required("admin")
def list_credit_applications():
    applications = db.session.scalars(db.select(CreditApplication).order_by(CreditApplication.created_at.desc())).all()
    return jsonify(
        applications=[
            application_payload(application)
            | {"business_id": application.business_id, "business_name": application.business.legal_name}
            for application in applications
        ]
    )


@admin_blueprint.patch("/credit-applications/<int:application_id>")
@roles_required("admin")
def review_credit_application(application_id: int):
    actor = get_current_user()
    application = db.session.get(CreditApplication, application_id)
    if application is None:
        return error("not_found", "Credit application not found.", 404)
    data = json_body()
    decision = clean_text(data.get("decision"), 16)
    if application.status != "pending":
        return error("already_reviewed", "This credit application was already reviewed.", 409)
    if decision not in {"approved", "rejected"}:
        return error("invalid_decision", "Decision must be approved or rejected.", 422)

    application.status = decision
    application.reviewed_by_user_id = actor.id
    application.reviewed_at = datetime.now(UTC)
    application.review_note = clean_text(data.get("review_note"), 1000) or None
    if decision == "approved":
        payment_days = data.get("payment_days")
        credit_limit = parse_decimal(data.get("credit_limit_usd"))
        if payment_days not in VALID_DAYS or credit_limit is None:
            return error("invalid_credit_terms", "Approved terms require 7, 15 or 30 days and a positive USD limit.", 422)
        db.session.execute(
            db.update(CreditTerms).where(CreditTerms.business_id == application.business_id, CreditTerms.is_active.is_(True)).values(is_active=False)
        )
        terms = CreditTerms(
            business_id=application.business_id,
            payment_days=payment_days,
            credit_limit_usd=credit_limit,
            approved_by_user_id=actor.id,
            note=application.review_note,
        )
        db.session.add(terms)
    audit(actor.id, f"credit.{decision}", "credit_application", application.id)
    db.session.commit()
    return jsonify(application=application_payload(application))


@admin_blueprint.patch("/businesses/<int:business_id>/credit-terms")
@roles_required("admin")
def update_credit_terms(business_id: int):
    actor = get_current_user()
    business = db.session.get(Business, business_id)
    if business is None:
        return error("not_found", "Business not found.", 404)
    data = json_body()
    payment_days = data.get("payment_days")
    credit_limit = parse_decimal(data.get("credit_limit_usd"))
    is_active = data.get("is_active", True)
    if payment_days not in VALID_DAYS or credit_limit is None or not isinstance(is_active, bool):
        return error("invalid_credit_terms", "Valid payment days, limit and active state are required.", 422)
    db.session.execute(
        db.update(CreditTerms).where(CreditTerms.business_id == business.id, CreditTerms.is_active.is_(True)).values(is_active=False)
    )
    terms = CreditTerms(
        business_id=business.id,
        payment_days=payment_days,
        credit_limit_usd=credit_limit,
        is_active=is_active,
        approved_by_user_id=actor.id,
        note=clean_text(data.get("note"), 1000) or None,
    )
    db.session.add(terms)
    audit(actor.id, "credit.terms_updated", "business", business.id, {"is_active": is_active})
    db.session.commit()
    return jsonify(credit_terms=credit_terms_payload(terms))


@admin_blueprint.get("/orders")
@roles_required("admin", "sales")
def list_orders():
    status = clean_text(__import__("flask").request.args.get("status"), 40)
    statement = db.select(Order).order_by(Order.id.desc())
    if status: statement = statement.where(Order.status == status)
    return jsonify(orders=[order_payload(order, include_payments=False) | {"business_id": order.business_id} for order in db.session.scalars(statement).all()])


@admin_blueprint.patch("/payment-submissions/<int:payment_id>")
@roles_required("admin", "sales")
def review_payment(payment_id: int):
    actor = get_current_user(); payment = db.session.get(PaymentSubmission, payment_id); data = json_body()
    if payment is None: return error("not_found", "Payment submission not found.", 404)
    decision = clean_text(data.get("decision"), 16)
    if payment.status != "submitted" or decision not in {"verified", "rejected"}: return error("invalid_payment_review", "A pending payment must be verified or rejected.", 422)
    note = clean_text(data.get("review_note"), 1000)
    if decision == "rejected" and not note: return error("review_note_required", "A rejection reason is required.", 422)
    payment.status = decision; payment.reviewed_by_user_id = actor.id; payment.reviewed_at = datetime.now(UTC); payment.review_note = note or None
    if decision == "verified": confirm_if_paid(payment.order, actor.id)
    audit(actor.id, f"payment.{decision}", "payment_submission", payment.id, {"order_id": payment.order_id}); db.session.commit()
    notify_order(payment.order, "confirmed" if decision == "verified" else "payment_rejected")
    return jsonify(order=order_payload(payment.order))


@admin_blueprint.get("/payment-submissions/<int:payment_id>/proof")
@roles_required("admin", "sales")
def payment_proof_url(payment_id: int):
    payment = db.session.get(PaymentSubmission, payment_id)
    if payment is None: return error("not_found", "Payment submission not found.", 404)
    try: return jsonify(url=read_url(payment.proof_storage_key))
    except StorageError: return error("storage_unavailable", "Payment proof storage is unavailable.", 503)


@admin_blueprint.post("/orders/<int:order_id>/cancel")
@roles_required("admin")
def cancel_order(order_id: int):
    actor = get_current_user(); order = db.session.get(Order, order_id); note = clean_text(json_body().get("note"), 1000)
    if order is None: return error("not_found", "Order not found.", 404)
    if order.status not in {"pending_payment", "payment_under_review", "pending_stock"}: return error("invalid_order_status", "Use the operational cancellation flow for this order.", 422)
    order.status = "cancelled"; order.cancelled_at = datetime.now(UTC); order.cancelled_by_user_id = actor.id
    if order.credit_usage and order.credit_usage.status == "active": order.credit_usage.status = "released"; order.credit_usage.released_at = datetime.now(UTC); order.credit_usage.released_by_user_id = actor.id; order.credit_usage.release_note = note or "Order cancelled"
    db.session.add(OrderStatusHistory(order_id=order.id, status="cancelled", note=note or None, actor_user_id=actor.id)); audit(actor.id, "order.cancelled", "order", order.id); db.session.commit()
    return jsonify(order=order_payload(order))
