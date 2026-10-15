import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "../api/client";
import type { CatalogProduct, ExchangeRate } from "../types";

type InvMovement = { id: number; variant: string; movement_type: string; quantity_delta: string; reason: string; created_at: string };

export function CatalogAdminPage() {
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [movements, setMovements] = useState<InvMovement[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showMovements, setShowMovements] = useState(false);

  async function load() {
    try {
      const [catalog, rateHistory] = await Promise.all([
        apiRequest<{ products: CatalogProduct[] }>("/api/admin/products"),
        apiRequest<{ exchange_rates: ExchangeRate[] }>("/api/admin/exchange-rates"),
      ]);
      setProducts(catalog.products);
      setRates(rateHistory.exchange_rates);
    } catch (item) { setError(item instanceof Error ? item.message : "No fue posible cargar catálogo e inventario."); }
  }
  useEffect(() => { load(); }, []);

  async function loadMovements() { try { const r = await apiRequest<{ movements: InvMovement[] }>("/api/admin/inventory/movements"); setMovements(r.movements); } catch {} }

  async function submitMovement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await apiRequest("/api/admin/inventory/movements", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
      event.currentTarget.reset();
      await load();
      if (showMovements) await loadMovements();
      setMessage("Movimiento de inventario registrado.");
    } catch (item) { setError(item instanceof Error ? item.message : "Error de inventario."); }
  }
  async function submitRate(event: FormEvent<HTMLFormElement>) { event.preventDefault(); try { await apiRequest("/api/admin/exchange-rates", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) }); event.currentTarget.reset(); await load(); setMessage("Tasa BCV registrada."); } catch (item) { setError(item instanceof Error ? item.message : "Error de tasa."); } }
  async function syncRate() { try { await apiRequest("/api/admin/exchange-rates/sync", { method: "POST" }); await load(); setMessage("Tasa BCV sincronizada."); } catch (item) { setError(item instanceof Error ? item.message : "No se pudo consultar BCV."); } }
  async function uploadImage(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); const productId = String(form.get("product_id")); const file = form.get("image") as File; if (!file?.size) return; try { const result = await apiRequest<{ upload: { upload_url: string; public_url: string } }>(`/api/admin/products/${productId}/image/upload`, { method: "POST", body: JSON.stringify({ filename: file.name, content_type: file.type, size_bytes: file.size }) }); const response = await fetch(result.upload.upload_url, { method: "PUT", headers: { "Content-Type": file.type }, body: file }); if (!response.ok) throw new Error("No fue posible cargar la imagen."); await apiRequest(`/api/admin/products/${productId}/image`, { method: "PATCH", body: JSON.stringify({ image_url: result.upload.public_url }) }); await load(); setMessage("Imagen de producto actualizada."); } catch (item) { setError(item instanceof Error ? item.message : "No fue posible guardar la imagen."); } }
  async function removeImage(product: CatalogProduct) { try { await apiRequest(`/api/admin/products/${product.id}/image`, { method: "DELETE" }); await load(); setMessage("Imagen eliminada."); } catch (item) { setError(item instanceof Error ? item.message : "No fue posible eliminar la imagen."); } }

  const variants = products.flatMap((product) => product.variants.map((variant) => ({ ...variant, productName: product.name, threshold: Number(variant.low_stock_threshold ?? "0") })));
  return (
    <main className="app-shell">
      <section className="page-header"><p className="eyebrow">Operación</p><h1>Catálogo, stock y tasa</h1></section>
      {message && <p className="notice">{message}</p>}{error && <p className="form-error">{error}</p>}
      <div className="grid admin-grid">
        {/* ─── Productos y existencias ─── */}
        <section className="card wide">
          <h2>Productos y existencias</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Producto</th><th>SKU</th><th>Precio USD</th><th>Stock actual</th><th>Umbral bajo</th></tr></thead>
              <tbody>
                {variants.map((variant) => {
                  const stock = Number(variant.stock ?? "0");
                  const low = stock > 0 && stock <= variant.threshold;
                  return (
                    <tr key={variant.id} className={low ? "row-warning" : stock <= 0 ? "row-danger" : ""}>
                      <td>{variant.productName}<small>{variant.name}</small></td>
                      <td>{variant.sku}</td>
                      <td>{variant.price_usd}</td>
                      <td className={low ? "text-warning" : stock <= 0 ? "text-danger" : ""}>{stock} {variant.inventory_unit}</td>
                      <td>{variant.low_stock_threshold ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* ─── Movimiento de inventario ─── */}
        <form className="card form" onSubmit={submitMovement}>
          <h2>Registrar movimiento</h2>
          <label>Producto<select name="variant_id">{variants.map((variant) => <option key={variant.id} value={variant.id}>{variant.productName} · {variant.name} ({variant.stock ?? "0"} {variant.inventory_unit})</option>)}</select></label>
          <input name="location_id" type="hidden" value="1" readOnly />
          <label>Tipo<select name="movement_type" defaultValue="incoming"><option value="incoming">➕ Ingreso</option><option value="outgoing">➖ Salida</option><option value="waste">🗑️ Merma</option><option value="adjustment">🔧 Ajuste</option></select></label>
          <label>Dirección<select name="direction" defaultValue="add"><option value="add">Sumar</option><option value="subtract">Restar</option></select></label>
          <label>Cantidad<input name="quantity" type="number" min="0.001" step="0.001" required /></label>
          <label>Motivo<input name="reason" required maxLength={500} placeholder="Ej: Ingreso de producción semanal" /></label>
          <button>Registrar movimiento</button>
        </form>

        {/* ─── Historial de movimientos ─── */}
        <section className="card">
          <h2>
            Historial
            {!showMovements && <button className="secondary" onClick={() => { setShowMovements(true); loadMovements(); }}>Mostrar</button>}
          </h2>
          {showMovements && movements.slice(0, 15).map((m) => (
            <p className="hint" key={m.id}>
              <strong>{m.movement_type}</strong> {m.variant}: {m.quantity_delta}
              <small>{m.reason} · {new Date(m.created_at).toLocaleString("es-VE")}</small>
            </p>
          ))}
        </section>

        {/* ─── Imagen de producto ─── */}
        <form className="card form" onSubmit={uploadImage}>
          <h2>Imagen de empaque</h2>
          <label>Producto<select name="product_id">{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></label>
          <label>Archivo JPG, PNG o WEBP<input name="image" type="file" accept="image/jpeg,image/png,image/webp" required /></label>
          <button>Subir imagen</button>
          {products.filter((p) => p.image_url).map((p) => <p className="hint" key={p.id}>{p.name} <button type="button" className="text-button dark" onClick={() => removeImage(p)}>Eliminar</button></p>)}
        </form>

        {/* ─── Tasa BCV ─── */}
        <section className="card">
          <h2>Tasa BCV</h2>
          <button onClick={syncRate}>Sincronizar desde BCV</button>
          <form className="form" onSubmit={submitRate}>
            <label>Tasa manual VES/USD<input name="rate_ves" type="number" min="0.01" step="0.01" required /></label>
            <label>Fecha efectiva<input name="effective_date" type="date" required /></label>
            <label>Motivo<input name="note" required /></label>
            <button>Registrar tasa</button>
          </form>
          {rates.slice(0, 5).map((rate) => <p className="hint" key={`${rate.effective_date}-${rate.rate_ves}`}>Bs. {rate.rate_ves} · {rate.effective_date}</p>)}
        </section>
      </div>
    </main>
  );
}