from decimal import Decimal, InvalidOperation

from flask import jsonify, request


def json_body() -> dict:
    return request.get_json(silent=True) or {}


def error(code: str, message: str, status: int = 400):
    return jsonify(error={"code": code, "message": message}), status


def clean_text(value: object, max_length: int = 255) -> str:
    return str(value or "").strip()[:max_length]


def parse_decimal(value: object) -> Decimal | None:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def user_payload(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "roles": sorted(role.code for role in user.roles),
    }


def business_payload(business) -> dict | None:
    if business is None:
        return None
    return {
        "id": business.id,
        "legal_name": business.legal_name,
        "tax_id": business.tax_id,
        "business_type": business.business_type,
        "contact_name": business.contact_name,
        "contact_email": business.contact_email,
        "contact_phone": business.contact_phone,
        "profile_status": business.profile_status,
        "is_active": business.is_active,
        "addresses": [
            {
                "id": address.id,
                "label": address.label,
                "line1": address.line1,
                "city": address.city,
                "state": address.state,
                "is_primary": address.is_primary,
            }
            for address in business.addresses
        ],
    }


def credit_terms_payload(terms) -> dict | None:
    if terms is None:
        return None
    return {
        "id": terms.id,
        "payment_days": terms.payment_days,
        "credit_limit_usd": str(terms.credit_limit_usd),
        "is_active": terms.is_active,
        "note": terms.note,
    }


def register_company_routes(app):
    @app.route("/api/company-info")
    def company_info():
        from flask import jsonify, current_app
        return jsonify(
            bank_name=current_app.config.get("BANK_NAME", "Banco del Cafe"),
            bank_rif=current_app.config.get("BANK_RIF", "J-1234567890"),
            bank_phone=current_app.config.get("BANK_PHONE", "0424-1234567"),
            platform_name=current_app.config.get("PLATFORM_NAME", "Tostaduria"),
        )
