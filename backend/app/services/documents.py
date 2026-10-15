from flask import current_app


def _html(title: str, number: str, business_name: str | None, items, total_usd, condition: str) -> str:
    rows = "".join(f"<tr><td>{item.product_name_snapshot}</td><td>{item.quantity}</td><td>USD {item.line_total_usd}</td></tr>" for item in items)
    return f"""<html><body style='font-family: sans-serif; color:#27362e'><h1>{current_app.config['PLATFORM_NAME']}</h1><h2>{title} {number}</h2><p>Cliente: {business_name or '—'}</p><table style='width:100%;border-collapse:collapse'><thead><tr><th>Producto</th><th>Cantidad</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table><h3>Total: USD {total_usd}</h3><p>Condición de pago: {condition}</p><hr><p>{current_app.config['PLATFORM_ADDRESS']}<br>{current_app.config['PLATFORM_PHONE']}</p></body></html>"""


def render_pdf(title: str, number: str, business_name: str | None, items, total_usd, condition: str) -> bytes:
    try:
        from weasyprint import HTML
        return HTML(string=_html(title, number, business_name, items, total_usd, condition)).write_pdf()
    except Exception:
        # Windows development environments often lack GTK/Pango. Render keeps
        # using the rich HTML renderer; this compact fallback keeps PDF download
        # available locally without adding platform-specific native libraries.
        lines = [current_app.config["PLATFORM_NAME"], f"{title} {number}", f"Cliente: {business_name or '—'}"]
        lines.extend(f"{item.product_name_snapshot} · {item.quantity} · USD {item.line_total_usd}" for item in items)
        lines.extend((f"Total: USD {total_usd}", f"Condición: {condition}"))
        content = "BT /F1 12 Tf 50 760 Td " + " ".join(f"({line.replace('(', '[').replace(')', ']')}) Tj 0 -18 Td" for line in lines) + " ET"
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>", f"<< /Length {len(content.encode())} >>\nstream\n{content}\nendstream".encode(), b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        result = b"%PDF-1.4\n"; offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(result)); result += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref = len(result); result += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
        return result + f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
