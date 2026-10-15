import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { apiDownload, apiRequest } from "../api/client";
import type { Order } from "../types";

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]); const [error, setError] = useState("");
  useEffect(() => { apiRequest<{ orders: Order[] }>("/api/orders").then((result) => setOrders(result.orders)).catch((item) => setError(item.message)); }, []);
  return <main className="app-shell"><section className="page-header"><p className="eyebrow">Compras</p><h1>Mis pedidos</h1></section>{error && <p className="form-error">{error}</p>}<section className="card table-wrap"><table><thead><tr><th>Pedido</th><th>Estado</th><th>Total</th><th>Saldo</th><th /></tr></thead><tbody>{orders.map((order) => <tr key={order.id}><td>{order.number}</td><td>{order.status}</td><td>USD {order.total_usd}</td><td>USD {order.outstanding_usd}</td><td><Link to={`/pedidos/${order.id}`}>Ver</Link></td></tr>)}</tbody></table>{orders.length === 0 && <p className="hint">Todavía no tienes pedidos.</p>}</section></main>;
}

export function OrderDetailPage() {
  const { id } = useParams(); const [order, setOrder] = useState<Order | null>(null); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const load = () => apiRequest<{ order: Order }>(`/api/orders/${id}`).then((result) => setOrder(result.order)).catch((item) => setError(item.message));
  useEffect(() => { load(); }, [id]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); const file = form.get("proof") as File;
    if (!file?.size) { setError("Selecciona un comprobante."); return; }
    try {
      const upload = await apiRequest<{ upload: { key: string; upload_url: string } }>(`/api/orders/${id}/payment-proofs/upload`, { method: "POST", body: JSON.stringify({ filename: file.name, content_type: file.type, size_bytes: file.size }) });
      const response = await fetch(upload.upload.upload_url, { method: "PUT", headers: { "Content-Type": file.type }, body: file }); if (!response.ok) throw new Error("No fue posible cargar el archivo.");
      await apiRequest(`/api/orders/${id}/payment-submissions`, { method: "POST", body: JSON.stringify({ currency: form.get("currency"), amount: form.get("amount"), reference: form.get("reference"), payment_method: form.get("payment_method"), note: form.get("note"), proof_storage_key: upload.upload.key, proof_original_filename: file.name, proof_content_type: file.type, proof_size_bytes: file.size }) });
      event.currentTarget.reset(); setMessage("Comprobante enviado para revisión."); await load();
    } catch (item) { setError(item instanceof Error ? item.message : "No fue posible enviar el comprobante."); }
  }
  async function download() { try { const blob = await apiDownload(`/api/orders/${id}/pdf`); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `pedido-${id}.pdf`; anchor.click(); URL.revokeObjectURL(url); } catch (item) { setError(item instanceof Error ? item.message : "No fue posible descargar el PDF."); } }
  if (!order) return <main className="app-shell"><p>{error || "Cargando pedido..."}</p></main>;
  const payable = !["confirmed", "cancelled"].includes(order.status);
  return <main className="app-shell"><Link to="/pedidos">← Mis pedidos</Link><section className="page-header"><p className="eyebrow">Pedido {order.number}</p><h1>{order.status}</h1><p>Saldo pendiente: <strong>USD {order.outstanding_usd}</strong></p><button className="secondary" onClick={download}>Descargar pedido PDF</button>{order.dispatch_guide && <p className="notice">Enviado por {order.dispatch_guide.carrier_name}{order.dispatch_guide.tracking_number ? ` · Tracking: ${order.dispatch_guide.tracking_number}` : ""}</p>}</section>{message && <p className="notice">{message}</p>}{error && <p className="form-error">{error}</p>}<div className="grid"><section className="card"><h2>Productos</h2>{order.items.map((item) => <p key={item.id}>{item.product_name} · {item.quantity} · USD {item.line_total_usd}</p>)}{order.estimated_dispatch_hours ? <p className="notice">Estimado de entrega: ~{order.estimated_dispatch_hours} horas{order.estimate_note ? ` · ${order.estimate_note}` : ""}</p> : <p className="hint">El equipo de Tostaduría publicará un estimado de entrega pronto.</p>}<h2>Progreso</h2>{order.history?.map((item, index) => <p className="hint" key={`${item.status}-${index}`}>{item.status} · {new Date(item.created_at).toLocaleString("es-VE")}{item.note ? ` — ${item.note}` : ""}</p>)}</section><section className="card"><h2>Comprobantes</h2>{order.payments?.map((payment) => <p key={payment.id}>{payment.reference} · USD {payment.amount_usd_equivalent} · <strong>{payment.status}</strong>{payment.review_note ? `: ${payment.review_note}` : ""}</p>)}{payable && <form className="form" onSubmit={submit}><label>Método<input name="payment_method" required placeholder="Transferencia" /></label><label>Moneda<select name="currency"><option>USD</option><option>VES</option></select></label><label>Monto<input name="amount" type="number" min="0.01" step="0.01" required /></label><label>Referencia<input name="reference" required maxLength={120} /></label><label>Comprobante (PDF, JPG, PNG o WEBP)<input name="proof" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required /></label><label>Nota<textarea name="note" maxLength={1000} /></label><button>Enviar comprobante</button></form>}</section></div></main>;
}
