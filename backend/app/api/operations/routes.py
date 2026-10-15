from datetime import UTC, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_current_user

from app.api.common import clean_text, error, json_body, parse_decimal
from app.extensions import db
from app.models import Order, OrderStatusHistory
from app.security import audit, roles_required
from app.services.operations import OperationError, complete_production, deliver_order, dispatch_order, restore_inventory, start_production, transition
from app.services.orders import order_payload
from app.services.notifications import notify_order

operations_blueprint = Blueprint("operations", __name__)


def _order_or_error(order_id: int):
    order = db.session.get(Order, order_id)
    return order


@operations_blueprint.get("/orders")
@roles_required("admin", "operator", "dispatch", "sales")
def list_orders():
    status = clean_text(request.args.get("status"), 40)
    statement = db.select(Order).order_by(Order.id.desc())
    if status: statement = statement.where(Order.status == status)
    return jsonify(orders=[order_payload(order, include_payments=False) | {"business_id": order.business_id} for order in db.session.scalars(statement).all()])


@operations_blueprint.get("/orders/<int:order_id>")
@roles_required("admin", "operator", "dispatch", "sales")
def get_order(order_id: int):
    order = _order_or_error(order_id)
    if order is None: return error("not_found", "Order not found.", 404)
    return jsonify(order=order_payload(order))


@operations_blueprint.patch("/orders/<int:order_id>/production/start")
@roles_required("admin", "operator")
def begin_production(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id)
    if order is None: return error("not_found", "Order not found.", 404)
    try: started = start_production(order, actor.id, clean_text(json_body().get("note"), 1000) or None)
    except OperationError as exc: return error("production_not_available", str(exc), 422)
    audit(actor.id, "order.production_started" if started else "order.pending_stock", "order", order.id); db.session.commit()
    if started: notify_order(order, "production")
    return jsonify(order=order_payload(order), started=started)


@operations_blueprint.patch("/orders/<int:order_id>/production/complete")
@roles_required("admin", "operator")
def finish_production(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id)
    if order is None: return error("not_found", "Order not found.", 404)
    try: complete_production(order, actor.id, clean_text(json_body().get("note"), 1000) or None)
    except OperationError as exc: return error("production_not_available", str(exc), 422)
    audit(actor.id, "order.production_completed", "order", order.id); db.session.commit(); return jsonify(order=order_payload(order))


@operations_blueprint.post("/orders/<int:order_id>/dispatch")
@roles_required("admin", "dispatch")
def create_dispatch(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id); data = json_body(); carrier = clean_text(data.get("carrier_name"), 160)
    if order is None: return error("not_found", "Order not found.", 404)
    if not carrier: return error("carrier_required", "A carrier name is required.", 422)
    try: dispatch_order(order, actor.id, carrier, clean_text(data.get("tracking_number"), 120) or None, clean_text(data.get("dispatch_note"), 1000) or None)
    except OperationError as exc: return error("dispatch_not_available", str(exc), 422)
    audit(actor.id, "order.dispatched", "order", order.id); db.session.commit(); notify_order(order, "dispatched"); return jsonify(order=order_payload(order)), 201


@operations_blueprint.patch("/orders/<int:order_id>/deliver")
@roles_required("admin", "dispatch")
def confirm_delivery(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id)
    if order is None: return error("not_found", "Order not found.", 404)
    try: deliver_order(order, actor.id, clean_text(json_body().get("note"), 1000) or None)
    except OperationError as exc: return error("delivery_not_available", str(exc), 422)
    audit(actor.id, "order.delivered", "order", order.id); db.session.commit(); notify_order(order, "delivered"); return jsonify(order=order_payload(order))


@operations_blueprint.post("/orders/<int:order_id>/return")
@roles_required("admin")
def process_return(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id); data = json_body(); reason = clean_text(data.get("reason"), 1000)
    if order is None: return error("not_found", "Order not found.", 404)
    if order.status != "delivered" or not reason: return error("return_not_available", "Only delivered orders with a reason can be returned.", 422)
    amounts = {}
    for item in data.get("items", []):
        quantity = parse_decimal(item.get("quantity")) if isinstance(item, dict) else None
        if quantity is None: return error("invalid_return", "Return quantities must be positive.", 422)
        amounts[int(item.get("order_item_id", 0))] = quantity
    try: restore_inventory(order, actor.id, f"Return: order {order.number} — {reason}", amounts or None)
    except OperationError as exc: return error("return_not_available", str(exc), 422)
    order.return_reason = reason; order.returned_at = datetime.now(UTC); transition(order, "returned", actor.id, reason); audit(actor.id, "order.returned", "order", order.id); db.session.commit(); notify_order(order, "returned", internal=True)
    return jsonify(order=order_payload(order))


@operations_blueprint.patch("/orders/<int:order_id>/estimate")
@roles_required("admin", "sales")
def set_order_estimate(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id); data = json_body()
    if order is None: return error("not_found", "Order not found.", 404)
    if "estimated_dispatch_hours" in data:
        hours = data.get("estimated_dispatch_hours")
        if hours is not None and (not isinstance(hours, int) or hours < 0): return error("invalid_hours", "Estimate hours must be a non-negative integer.", 422)
        order.estimated_dispatch_hours = hours
    if "estimate_note" in data:
        order.estimate_note = clean_text(data["estimate_note"], 500) or None
    audit(actor.id, "order.estimate_updated", "order", order.id, {"hours": order.estimated_dispatch_hours}); db.session.commit()
    return jsonify(order=order_payload(order))


@operations_blueprint.patch("/orders/<int:order_id>/cancel")
@roles_required("admin")
def cancel_operational_order(order_id: int):
    actor = get_current_user(); order = _order_or_error(order_id); note = clean_text(json_body().get("note"), 1000)
    if order is None: return error("not_found", "Order not found.", 404)
    if order.status in {"cancelled", "delivered", "returned"}: return error("invalid_order_status", "This order cannot be cancelled.", 422)
    if order.status in {"in_production", "ready", "dispatched"}:
        try: restore_inventory(order, actor.id, f"Cancellation: order {order.number}")
        except OperationError as exc: return error("cancellation_not_available", str(exc), 422)
    order.cancelled_at = datetime.now(UTC); order.cancelled_by_user_id = actor.id; transition(order, "cancelled", actor.id, note or "Order cancelled.")
    if order.credit_usage and order.credit_usage.status == "active": order.credit_usage.status = "released"; order.credit_usage.released_at = datetime.now(UTC); order.credit_usage.released_by_user_id = actor.id; order.credit_usage.release_note = note or "Order cancelled"
    audit(actor.id, "order.cancelled", "order", order.id); db.session.commit(); return jsonify(order=order_payload(order))
