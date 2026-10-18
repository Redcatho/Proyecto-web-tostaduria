from flask import Blueprint, jsonify
from flask_jwt_extended import get_current_user, jwt_required

from app.api.common import business_payload, clean_text, error, json_body
from app.extensions import db
from app.models import Business, BusinessAddress, BusinessMembership
from app.security import audit

businesses_blueprint = Blueprint("businesses", __name__)
BUSINESS_TYPES = {"cafeteria", "supermarket", "wholesaler"}


def current_business(user) -> Business | None:
    membership = db.session.scalar(
        db.select(BusinessMembership).where(BusinessMembership.user_id == user.id).order_by(BusinessMembership.is_owner.desc())
    )
    return membership.business if membership else None


def update_profile_status(business: Business) -> None:
    required = (
        business.legal_name,
        business.tax_id,
        business.business_type,
        business.contact_name,
        business.contact_email,
    )
    business.profile_status = "complete" if all(required) and business.addresses else "incomplete"


@businesses_blueprint.get("/me")
@jwt_required()
def get_business():
    return jsonify(business=business_payload(current_business(get_current_user())))


@businesses_blueprint.patch("/me")
@jwt_required()
def update_business():
    user = get_current_user()
    data = json_body()
    business = current_business(user)
    if business is None:
        business = Business()
        db.session.add(business)
        db.session.flush()
        db.session.add(BusinessMembership(user_id=user.id, business_id=business.id, is_owner=True))

    legal_name = clean_text(data.get("legal_name"), 180)
    tax_id = clean_text(data.get("tax_id"), 32).upper()
    business_type = clean_text(data.get("business_type"), 32)
    contact_name = clean_text(data.get("contact_name"), 160)
    contact_email = clean_text(data.get("contact_email")).lower()
    contact_phone = clean_text(data.get("contact_phone"), 40)
    if business_type and business_type not in BUSINESS_TYPES:
        return error("invalid_business_type", "Business type is invalid.", 422)
    if tax_id:
        duplicate = db.session.scalar(db.select(Business).where(Business.tax_id == tax_id, Business.id != business.id))
        if duplicate:
            return error("tax_id_unavailable", "This RIF or identification is already registered.", 409)

    business.legal_name = legal_name or None
    business.tax_id = tax_id or None
    business.business_type = business_type or None
    business.contact_name = contact_name or None
    business.contact_email = contact_email or None
    business.contact_phone = contact_phone or None
    update_profile_status(business)
    audit(user.id, "business.profile_updated", "business", business.id)
    db.session.commit()
    return jsonify(business=business_payload(business))


@businesses_blueprint.post("/me/addresses")
@jwt_required()
def create_address():
    user = get_current_user()
    business = current_business(user)
    if business is None:
        return error("business_required", "Create the business profile first.", 422)
    data = json_body()
    line1 = clean_text(data.get("line1"))
    city = clean_text(data.get("city"), 120)
    state = clean_text(data.get("state"), 120)
    if not line1 or not city or not state:
        return error("invalid_address", "Address, city and state are required.", 422)
    make_primary = bool(data.get("is_primary")) or not business.addresses
    if make_primary:
        for address in business.addresses:
            address.is_primary = False
    address = BusinessAddress(
        business=business,
        label=clean_text(data.get("label"), 80) or "Principal",
        line1=line1,
        city=city,
        state=state,
        is_primary=make_primary,
    )
    db.session.add(address)
    db.session.flush()
    update_profile_status(business)
    audit(user.id, "business.address_created", "business_address", address.id)
    db.session.commit()
    return jsonify(address={"id": address.id}), 201


@businesses_blueprint.patch("/me/addresses/<int:address_id>")
@jwt_required()
def update_address(address_id: int):
    user = get_current_user()
    business = current_business(user)
    address = db.session.get(BusinessAddress, address_id)
    if business is None or address is None or address.business_id != business.id:
        return error("not_found", "Address not found.", 404)
    data = json_body()
    for field, max_length in (("label", 80), ("line1", 255), ("city", 120), ("state", 120)):
        if field in data:
            value = clean_text(data[field], max_length)
            if not value:
                return error("invalid_address", f"{field} cannot be empty.", 422)
            setattr(address, field, value)
    if data.get("is_primary"):
        for item in business.addresses:
            item.is_primary = item.id == address.id
    update_profile_status(business)
    audit(user.id, "business.address_updated", "business_address", address.id)
    db.session.commit()
    return jsonify(business=business_payload(business))
