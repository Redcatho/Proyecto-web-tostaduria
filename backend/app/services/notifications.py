from app.services.mail import send_email
from app.services.telegram import send_telegram


def _customer_email(order):
    return order.quote.business.contact_email if getattr(order, "quote", None) and order.quote.business else None


def notify_order(order, event: str, internal: bool = False) -> None:
    labels = {"created": "Pedido recibido", "payment_review": "Pago recibido para revisión", "confirmed": "Pedido confirmado", "production": "Pedido en producción", "ready": "Pedido listo", "dispatched": "Pedido despachado", "delivered": "Pedido entregado", "returned": "Devolución procesada"}
    label = labels.get(event, "Actualización de pedido")
    if event in {"created", "payment_review", "ready", "returned"}:
        send_telegram(f"{label}: {order.number} · estado {order.status}")
    if not internal and event not in {"ready", "returned"}:
        send_email(_customer_email(order), f"{label} · {order.number}", f"<h1>{label}</h1><p>Tu pedido <strong>{order.number}</strong> ahora está en estado <strong>{order.status}</strong>.</p>")
