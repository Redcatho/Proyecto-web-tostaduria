from datetime import UTC, datetime
from decimal import Decimal

from app.extensions import db
from app.models import DispatchGuide, InventoryBalance, InventoryLocation, InventoryMovement, Order, OrderStatusHistory, QuoteItem

OPERATIONAL_STATUSES = {"confirmed", "in_production", "pending_stock", "ready", "dispatched", "delivered", "returned", "cancelled"}


class OperationError(ValueError):
    pass


def transition(order: Order, status: str, actor_id: int, note: str | None = None) -> None:
    order.status = status
    db.session.add(OrderStatusHistory(order_id=order.id, status=status, note=note, actor_user_id=actor_id))


def _location() -> InventoryLocation:
    location = db.session.scalar(db.select(InventoryLocation).where(InventoryLocation.is_active.is_(True)).order_by(InventoryLocation.id))
    if location is None:
        raise OperationError("No active inventory location is configured.")
    return location


def _order_variants(order: Order):
    rows = []
    for item in order.items:
        quote_item = db.session.get(QuoteItem, item.quote_item_id) if item.quote_item_id else None
        if quote_item is None or quote_item.variant_id is None:
            raise OperationError(f"The source variant for {item.product_name_snapshot} is unavailable.")
        rows.append((item, quote_item.variant_id, Decimal(item.quantity)))
    return rows


def start_production(order: Order, actor_id: int, note: str | None = None) -> bool:
    if order.status not in {"confirmed", "pending_stock"}:
        raise OperationError("Only confirmed or stock-pending orders can begin production.")
    location = _location(); lines = _order_variants(order); balances = []
    for item, variant_id, quantity in lines:
        balance = db.session.scalar(db.select(InventoryBalance).where(InventoryBalance.variant_id == variant_id, InventoryBalance.location_id == location.id).with_for_update())
        if balance is None or Decimal(balance.quantity) < quantity:
            transition(order, "pending_stock", actor_id, f"Insufficient stock for {item.product_name_snapshot}.")
            return False
        balances.append((item, variant_id, quantity, balance))
    for item, variant_id, quantity, balance in balances:
        balance.quantity = Decimal(balance.quantity) - quantity
        db.session.add(InventoryMovement(variant_id=variant_id, location_id=location.id, movement_type="outgoing", quantity_delta=-quantity, reason=f"Production: order {order.number}", actor_user_id=actor_id))
    order.production_started_at = datetime.now(UTC); order.production_started_by_user_id = actor_id; order.production_notes = note or None
    transition(order, "in_production", actor_id, note or "Production started.")
    return True


def complete_production(order: Order, actor_id: int, note: str | None = None) -> None:
    if order.status != "in_production": raise OperationError("Only orders in production can be marked ready.")
    transition(order, "ready", actor_id, note or "Production completed.")


def dispatch_order(order: Order, actor_id: int, carrier_name: str, tracking_number: str | None, note: str | None) -> DispatchGuide:
    if order.status != "ready": raise OperationError("Only ready orders can be dispatched.")
    if order.dispatch_guide is not None: raise OperationError("A dispatch guide already exists for this order.")
    guide = DispatchGuide(order_id=order.id, prepared_by_user_id=actor_id, carrier_name=carrier_name, tracking_number=tracking_number or None, dispatch_note=note or None)
    db.session.add(guide); transition(order, "dispatched", actor_id, note or f"Dispatched by {carrier_name}.")
    return guide


def deliver_order(order: Order, actor_id: int, note: str | None = None) -> None:
    if order.status != "dispatched" or order.dispatch_guide is None: raise OperationError("Only dispatched orders with a guide can be delivered.")
    now = datetime.now(UTC); order.delivered_at = now; order.dispatch_guide.delivered_at = now; order.dispatch_guide.delivery_confirmed_by_user_id = actor_id
    transition(order, "delivered", actor_id, note or "Delivery confirmed.")


def restore_inventory(order: Order, actor_id: int, reason: str, return_quantities: dict[int, Decimal] | None = None) -> None:
    location = _location()
    for item, variant_id, quantity in _order_variants(order):
        amount = return_quantities.get(item.id, Decimal("0")) if return_quantities is not None else quantity
        if amount == 0:
            continue
        if amount < 0 or amount > quantity: raise OperationError("Return quantities cannot exceed the order quantity.")
        balance = db.session.scalar(db.select(InventoryBalance).where(InventoryBalance.variant_id == variant_id, InventoryBalance.location_id == location.id).with_for_update())
        if balance is None:
            balance = InventoryBalance(variant_id=variant_id, location_id=location.id, quantity=0); db.session.add(balance); db.session.flush()
        balance.quantity = Decimal(balance.quantity) + amount
        db.session.add(InventoryMovement(variant_id=variant_id, location_id=location.id, movement_type="incoming", quantity_delta=amount, reason=reason, actor_user_id=actor_id))
