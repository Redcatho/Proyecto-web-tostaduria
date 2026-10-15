import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiRequest } from "../api/client";

type Quote = { id: number; number: string; status: string; total_usd: string; total_ves: string; rate_ves: string; rate_effective_date: string; required_advance_usd: string; estimated_dispatch_hours: number | null; estimate_note: string | null; expires_at: string; items: { sku: string; product_name: string; quantity: string; roast_profile: string | null; line_total_usd: string }[] };

export function QuoteDetailPage() {
  const { id } = useParams(); const navigate = useNavigate(); const [quote, setQuote] = useState<Quote | null>(null); const [error, setError] = useState("");
  useEffect(() => { apiRequest<{ quote: Quote }>(`/api/quotes/${id}`).then((result) => setQuote(result.quote)).catch((item) => setError(item instanceof Error ? item.message : "No fue posible cargar la cotización.")); }, [id]);
  async function accept() { try { const result = await apiRequest<{ order: { id: number; number: string } }>(`/api/quotes/${id}/accept`, { method: "POST" }); navigate(`/pedidos/${result.order.id}`, { state: { message: `Pedido ${result.order.number} creado.` } }); } catch (item) { setError(item instanceof Error ? item.message : "No fue posible aceptar la cotización."); } }
  if (error) return <main className="app-shell"><p className="form-error">{error}</p><Link to="/carrito">Volver al carrito</Link></main>;
  if (!quote) return <main className="app-shell"><p>Cargando cotización...</p></main>;
  return <main className="cart-shell"><section><p className="eyebrow">Cotización {quote.number}</p><h1>Lista para confirmar.</h1><p className="rate-note">Vence: {new Date(quote.expires_at).toLocaleString("es-VE")}</p><div className="cart-list">{quote.items.map((item) => <article className="cart-row" key={item.sku + item.roast_profile}><div className="cart-thumb">Café</div><div><h2>{item.product_name}</h2><p>{item.quantity} · {item.roast_profile?.replace("_", " ") ?? "Presentación fija"}</p></div><div className="cart-price"><strong>USD {item.line_total_usd}</strong></div></article>)}</div></section><aside className="cart-summary"><p className="eyebrow">Resumen final</p><div className="summary-total"><span>Total</span><strong>USD {quote.total_usd}</strong></div><p>Bs. {quote.total_ves}<small>BCV {quote.rate_ves} · {quote.rate_effective_date}</small></p><p>Anticipo requerido: <strong>USD {quote.required_advance_usd}</strong></p><p>{quote.estimate_note ?? (quote.estimated_dispatch_hours ? `Estimado: ${quote.estimated_dispatch_hours} horas.` : "Pendiente de revisión.")}</p>{quote.status === "issued" && <button onClick={accept}>Aceptar y crear pedido</button>}</aside></main>;
}
