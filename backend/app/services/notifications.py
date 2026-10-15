from app.services.mail import send_email
from app.services.telegram import send_telegram


def _customer_email(order):
    return order.quote.business.contact_email if getattr(order, 'quote', None) and order.quote.business else None


def _customer_name(order):
    return order.quote.business.legal_name if getattr(order, 'quote', None) and order.quote.business else 'Cliente'


def _items_summary(order) -> str:
    parts = []
    for item in order.items:
        name = item.product_name_snapshot
        qty = str(item.quantity) if item.quantity is not None else '0'
        parts.append(name + ' x ' + qty)
    return ' / '.join(parts) if parts else chr(8212)


def notify_order(order, event: str, internal: bool = False) -> None:
    number = order.number
    name = _customer_name(order)
    items = _items_summary(order)
    total = str(order.total_usd) if order.total_usd else '---'

    if event == 'created':
        condition = order.payment_condition or '---'
        payment = {'advance_50': 'Anticipo 50%', 'full_payment': 'Pago completo', 'credit': 'Credito'}.get(condition, condition)
        telegram_msg = (
            chr(128230) + ' Nuevo pedido: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Total: USD ' + total + chr(10) +
            'Condicion: ' + payment + chr(10) +
            'Productos: ' + items
        )
        email_subject = 'Pedido recibido - ' + number
        email_body = '<h1>Pedido recibido</h1><p>Hola <strong>' + name + '</strong>,</p><p>Recibimos tu pedido <strong>' + number + '</strong> por un total de <strong>USD ' + total + '</strong>.</p><p>Productos: ' + items + '</p><p>Condicion de pago: ' + payment + '</p><p>Te notificaremos cuando el pago sea verificado.</p>'

    elif event == 'payment_review':
        telegram_msg = (
            chr(128176) + ' Pago por revisar: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Total pedido: USD ' + total + chr(10) +
            'Productos: ' + items
        )
        email_subject = 'Pago recibido para revision - ' + number
        email_body = '<h1>Pago en revision</h1><p>Hola <strong>' + name + '</strong>,</p><p>Hemos recibido tu comprobante de pago para el pedido <strong>' + number + '</strong>.</p><p>Nuestro equipo lo revisara a la brevedad. Te avisaremos cuando este verificado.</p>'

    elif event == 'confirmed':
        telegram_msg = (
            chr(10004) + ' Pago verificado - Pedido confirmado: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Total: USD ' + total + chr(10) +
            'Productos: ' + items
        )
        email_subject = 'Pedido confirmado - ' + number
        email_body = '<h1>Pedido confirmado</h1><p>Hola <strong>' + name + '</strong>,</p><p>Tu pago para el pedido <strong>' + number + '</strong> ha sido verificado. El pedido esta <strong>confirmado</strong> y pasara a produccion en breve.</p><p>Te mantendremos informado del progreso.</p>'

    elif event == 'payment_rejected':
        telegram_msg = None
        email_subject = 'Comprobante rechazado - ' + number
        email_body = '<h1>Comprobante de pago rechazado</h1><p>Hola <strong>' + name + '</strong>,</p><p>El comprobante que enviaste para el pedido <strong>' + number + '</strong> no pudo ser verificado.</p><p>Por favor revisa los datos e intenta nuevamente desde el detalle del pedido.</p>'

    elif event == 'production':
        telegram_msg = (
            chr(127981) + ' Produccion iniciada: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Total: USD ' + total + chr(10) +
            'Productos: ' + items
        )
        email_subject = 'Pedido en produccion - ' + number
        email_body = '<h1>Pedido en produccion</h1><p>Hola <strong>' + name + '</strong>,</p><p>Tu pedido <strong>' + number + '</strong> ha entrado en produccion.</p><p>Productos: ' + items + '</p><p>Te avisaremos cuando este listo para despachar.</p>'

    elif event == 'ready':
        telegram_msg = (
            chr(128230) + ' Pedido listo para despachar: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Total: USD ' + total + chr(10) +
            'Productos: ' + items
        )
        email_subject = 'Pedido listo - ' + number
        email_body = '<h1>Pedido listo para despachar</h1><p>Hola <strong>' + name + '</strong>,</p><p>Tu pedido <strong>' + number + '</strong> esta listo. Pasaremos a preparar el despacho en las proximas horas.</p><p>Recibiras una notificacion con los datos de la guia cuando este en camino.</p>'

    elif event == 'dispatched':
        guide = order.dispatch_guide
        carrier = guide.carrier_name if guide else '---'
        tracking = guide.tracking_number if guide and guide.tracking_number else '---'
        telegram_msg = (
            chr(128666) + ' Pedido despachado: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Transportista: ' + carrier + chr(10) +
            'Tracking: ' + tracking
        )
        email_subject = 'Pedido despachado - ' + number
        email_body = '<h1>Pedido despachado</h1><p>Hola <strong>' + name + '</strong>,</p><p>Tu pedido <strong>' + number + '</strong> ha sido despachado.</p><p>Transportista: ' + carrier + '<br>Tracking: ' + tracking + '</p>'

    elif event == 'delivered':
        telegram_msg = None
        email_subject = 'Pedido entregado - ' + number
        email_body = '<h1>Pedido entregado</h1><p>Hola <strong>' + name + '</strong>,</p><p>Tu pedido <strong>' + number + '</strong> ha sido entregado. Gracias por confiar en Tostaduria!</p><p>Si tienes algun inconveniente, no dudes en contactarnos.</p>'

    elif event == 'returned':
        reason = order.return_reason or '---'
        telegram_msg = (
            chr(128260) + ' Devolucion procesada: ' + number + chr(10) +
            'Cliente: ' + name + chr(10) +
            'Motivo: ' + reason
        )
        email_subject = 'Devolucion procesada - ' + number
        email_body = '<h1>Devolucion procesada</h1><p>Hola <strong>' + name + '</strong>,</p><p>Se ha procesado la devolucion del pedido <strong>' + number + '</strong>.</p><p>Motivo: ' + reason + '</p>'

    else:
        telegram_msg = None
        email_subject = 'Actualizacion de pedido - ' + number
        email_body = '<h1>Actualizacion</h1><p>Tu pedido ' + number + ' ha cambiado de estado.</p>'

    # Send Telegram for operational events
    if event in {'created', 'payment_review', 'ready', 'returned', 'confirmed', 'production', 'dispatched'}:
        if telegram_msg:
            send_telegram(telegram_msg)

    # Send email to customer for all events except internal-only ones
    if not internal:
        recipient = _customer_email(order)
        if recipient and email_subject and email_body:
            send_email(recipient, email_subject, email_body)
