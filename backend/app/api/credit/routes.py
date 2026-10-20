from flask import Blueprint, jsonify
from flask_jwt_extended import get_current_user, jwt_required

from app.api.businesses.routes import current_business
from app.api.common import clean_text, credit_terms_payload, error, json_body, parse_decimal
from app.extensions import db
from app.models import CreditApplication, CreditTerms
from app.security import audit

credit_blueprint = Blueprint("credit", __name__)
VALID_DAYS = {7, 15, 30}


def application_payload(application: CreditApplication) -> dict:
    return {
        "id": application.id,
        "requested_days": application.requested_days,
        "requested_limit_usd": str(application.requested_limit_usd),
        "justification": application.justification,
        "status": application.status,
        "review_note": application.review_note,
        "created_at": application.created_at.isoformat(),
    }


@credit_blueprint.get("/me")
@jwt_required()
def list_credit_status():
    business = current_business(get_current_user())
    if business is None:
        return jsonify(applications=[], active_terms=None)
    applications = db.session.scalars(
        db.select(CreditApplication).where(CreditApplication.business_id == business.id).order_by(CreditApplication.id.desc())
    ).all()
    terms = db.session.scalar(
        db.select(CreditTerms).where(CreditTerms.business_id == business.id, CreditTerms.is_active.is_(True)).order_by(CreditTerms.id.desc())
    )
    return jsonify(applications=[application_payload(item) for item in applications], active_terms=credit_terms_payload(terms))


@credit_blueprint.post("")
@jwt_required()
def create_credit_application():
    user = get_current_user()
    business = current_business(user)
    if business is None or business.profile_status != "complete":
        return error("complete_business_required", "Complete the business profile before requesting credit.", 422)
    data = json_body()
    requested_days = data.get("requested_days")
    requested_limit = parse_decimal(data.get("requested_limit_usd"))
    try: requested_days = int(requested_days)
    except (TypeError, ValueError): requested_days = None
    if requested_days not in VALID_DAYS or requested_limit is None:
        return error("invalid_credit_request", "Choose 7, 15 or 30 days and a positive USD limit.", 422)
    pending = db.session.scalar(
        db.select(CreditApplication).where(CreditApplication.business_id == business.id, CreditApplication.status == "pending")
    )
    if pending:
        return error("credit_request_pending", "There is already a credit request under review.", 409)
    application = CreditApplication(
        business_id=business.id,
        requested_days=requested_days,
        requested_limit_usd=requested_limit,
        justification=clean_text(data.get("justification"), 1000) or None,
    )
    db.session.add(application)
    db.session.flush()
    audit(user.id, "credit.requested", "credit_application", application.id)
    db.session.commit()
    return jsonify(application=application_payload(application)), 201
