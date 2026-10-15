from datetime import UTC, datetime
from decimal import Decimal

from app.extensions import db
from app.models import CreditTerms, CreditUsage, Order, OrderStatusHistory, PaymentSubmission


def payment_payload(payment: PaymentSubmission) -> dict:
    return {"id": payment.id, "currency": payment.currency, "amount": str(payment.amount), "amount_usd_equivalent": str(payment.amount_usd_equivalent), "reference": payment.reference, "payment_method": payment.payment_method, "proof_original_filename": payment.proof_original_filename, "proof_content_type": payment.proof_content_type, "proof_size_bytes": payment.proof_size_bytes, "note": payment.note, "status": payment.status, "review_note": payment.review_note, "submitted_at": payment.submitted_at.isoformat(), "reviewed_at": payment.reviewed_at.isoformat() if payment.reviewed_at else None}


def verified_total(order: Order) -> Decimal:
    return sum((Decimal(item.amount_usd_equivalent) for item in order.payments if item.status == "verified"), Decimal("0"))


def order_payload(order: Order, include_payments: bool = True) -> dict:
    required = Decimal(order.required_payment_usd or 0)
    paid = verified_total(order)
    guide = order.dispatch_guide
    payload = {"id": order.id, "number": order.number, "status": order.status, "payment_condition": order.payment_condition, "total_usd": str(order.total_usd) if order.total_usd is not None else None, "total_ves": str(order.total_ves) if order.total_ves is not None else None, "rate_ves": str(order.rate_ves) if order.rate_ves is not None else None, "rate_effective_date": order.rate_effective_date.isoformat() if order.rate_effective_date else None, "required_payment_usd": str(required), "verified_payment_usd": str(paid), "outstanding_usd": str(max(Decimal("0"), required - paid)), "created_at": order.created_at.isoformat(), "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None, "production_started_at": order.production_started_at.isoformat() if order.production_started_at else None, "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None, "estimated_dispatch_hours": order.estimated_dispatch_hours, "estimate_note": order.estimate_note, "dispatch_guide": {"carrier_name": guide.carrier_name, "tracking_number": guide.tracking_number, "dispatch_note": guide.dispatch_note, "dispatched_at": guide.dispatched_at.isoformat()} if guide else None, "history": [{"status": item.status, "note": item.note, "created_at": item.created_at.isoformat()} for item in db.session.scalars(db.select(OrderStatusHistory).where(OrderStatusHistory.order_id == order.id).order_by(OrderStatusHistory.id)).all()], "items": [{"id": item.id, "sku": item.sku_snapshot, "product_name": item.product_name_snapshot, "quantity": str(item.quantity), "roast_profile": item.roast_profile, "line_total_usd": str(item.line_total_usd)} for item in order.items]}
    if include_payments:
        payload["payments"] = [payment_payload(item) for item in order.payments]
    return payload


def credit_available(business_id: int, terms: CreditTerms) -> Decimal:
    active = db.session.scalar(db.select(db.func.coalesce(db.func.sum(CreditUsage.amount_usd), 0)).where(CreditUsage.business_id == business_id, CreditUsage.status == "active"))
    return Decimal(terms.credit_limit_usd) - Decimal(active or 0)


def confirm_if_paid(order: Order, actor_id: int | None) -> bool:
    if order.status in {"cancelled", "confirmed"} or verified_total(order) < Decimal(order.required_payment_usd or 0):
        return False
    order.status = "confirmed"
    order.confirmed_at = datetime.now(UTC)
    db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed", note="Required payment verified.", actor_user_id=actor_id))
    return True
