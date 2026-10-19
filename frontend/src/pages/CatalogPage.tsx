import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../api/client";
import type { CatalogProduct, ExchangeRate } from "../types";

const roastOptions: { value: string; label: string }[] = [
  { value: "claro", label: "Claro" },
  { value: "medio", label: "Medio" },
  { value: "medio_alto", label: "Medio alto" },
  { value: "alto", label: "Alto" },
];

type VariantInfo = { id: number; name: string; price_usd: string; price_ves: string | null; sale_unit: string; availability: string; stock?: string };

function VariantStepper({ variant, productLine, authenticated, onAdd }: { variant: VariantInfo; productLine: string; authenticated: boolean; onAdd: () => void }) {
  const step = productLine === "cafeteria" ? 5 : 1;
  const min = 1;
  const [quantity, setQuantity] = useState<number>(step);
  const [roastProfile, setRoastProfile] = useState<string>("medio");
  const [adding, setAdding] = useState<boolean>(false);

  async function addToCart() {
    if (!authenticated) { window.location.href = "/ingresar"; return; }
    setAdding(true);
    try {
      await apiRequest("/api/cart/items", { method: "POST", body: JSON.stringify({ variant_id: variant.id, quantity: String(quantity), roast_profile: productLine === "cafeteria" ? roastProfile : null }) });
      onAdd();
    } catch { /* The cart page will show server validation. */ } finally { setAdding(false); }
  }

  return (
    <div className="variant-stepper">
      <div className="stepper">
        <button type="button" className="stepper-btn" onClick={() => setQuantity(Math.max(min, quantity - step))} disabled={quantity <= min}>−</button>
        <input type="number" min={min} step={step} value={quantity} onChange={(event) => { const v = Number(event.target.value); if (v >= min) setQuantity(v); }} />
        <button type="button" className="stepper-btn" onClick={() => setQuantity(quantity + step)}>+</button>
      </div>
      {productLine === "cafeteria" && (
        <select className="roast-select" value={roastProfile} onChange={(event) => setRoastProfile(event.target.value)}>
          {roastOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      )}
      <button className="add-cart-btn" disabled={adding} onClick={addToCart}>{adding ? "Agregando..." : "Agregar al carrito"}</button>
    </div>
  );
}

export function CatalogPage({ authenticated = false, onCartUpdate }: { authenticated?: boolean; onCartUpdate?: () => void }) {
  const navigate = useNavigate();
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const [line, setLine] = useState<string>("all");
  const [toast, setToast] = useState<string | null>(null);
  const [calcUsd, setCalcUsd] = useState<string>("100");

  useEffect(() => {
    apiRequest<{ products: CatalogProduct[]; exchange_rate: ExchangeRate | null }>("/api/catalog/products")
      .then((result) => { setProducts(result.products); setRate(result.exchange_rate); })
      .catch(() => setProducts([]));
  }, []);

  function added() {
    if (onCartUpdate) onCartUpdate();
    setToast("Agregado al carrito ✓");
    setTimeout(() => setToast(null), 5000);
  }

  const visible = products.filter((product) => line === "all" || product.line === line);
  const calcVes = rate && calcUsd ? (Number(calcUsd) * Number(rate.rate_ves)).toLocaleString("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
  const rateLine = rate
    ? <p className="rate-note">💱 Tasa BCV: 1 USD = <strong>Bs. {rate.rate_ves}</strong> · {rate.effective_date}</p>
    : <p className="rate-note">La tasa BCV se actualizará próximamente.</p>;

  return (
    <main className="catalog-shell">
      {toast && (
        <div className="catalog-toast">
          <span>{toast}</span>
          <Link to="/carrito" className="toast-btn">Ir al carrito</Link>
          <button className="toast-btn secondary" onClick={() => setToast(null)}>Seguir comprando</button>
        </div>
      )}
      <section className="catalog-intro">
        <p className="eyebrow">Tostaduria · Caracas</p>
        <h1>Café para operación y anaquel.</h1>
        <p>Presentaciones comerciales listas para tienda y café en grano para cafeterías.</p>
        <div className="catalog-actions">
          <button className={line === "all" ? "selected" : "secondary"} onClick={() => setLine("all")}>Todo</button>
          <button className={line === "commercial" ? "selected" : "secondary"} onClick={() => setLine("commercial")}>Comercial</button>
          <button className={line === "cafeteria" ? "selected" : "secondary"} onClick={() => setLine("cafeteria")}>Cafeterías</button>
        </div>
        {rateLine}
        {rate && <div className="rate-calc"><label>💰 Convertir a Bs.<div className="calc-row"><span className="calc-label">USD</span><input type="number" min="0" step="any" value={calcUsd} onChange={(e) => setCalcUsd(e.target.value)} /></div><div className="calc-row"><span className="calc-label">Bs.</span><strong>{calcVes}</strong></div></label></div>}
      </section>
      <section className="product-grid">
        {visible.map((product) => (
          <article className="product-card" key={product.id}>
            <div className="product-image">{product.image_url ? <img src={product.image_url} alt="" /> : <span>{product.line === "commercial" ? "Bulto comercial" : "Café en grano"}</span>}</div>
            <p className="eyebrow">{product.line === "commercial" ? "Línea comercial" : "Para cafeterías"}</p>
            <h2>{product.name}</h2>
            <p>{product.description}</p>
            {product.origin && <p className="hint">{product.origin}{product.variety ? ` · ${product.variety}` : ""}</p>}
            {product.variants.map((variant) => (
              <div className="variant" key={variant.id}>
                <strong>{variant.name}</strong>
                <span>USD {variant.price_usd} {variant.sale_unit === "kg" ? "por kg" : "por bulto"}</span>
                {variant.price_ves && <small>Bs. {variant.price_ves}</small>}
                <em className={`availability availability--${variant.availability.replace(" ", "-").toLowerCase()}`}>{variant.availability}</em>
                {variant.availability !== "Agotado" && <VariantStepper variant={variant} productLine={product.line} authenticated={authenticated} onAdd={added} />}
              </div>
            ))}
          </article>
        ))}
      </section>
      {!authenticated && <p className="catalog-login">¿Ya eres cliente? <Link to="/ingresar">Ingresa a tu cuenta</Link> para comprar.</p>}
    </main>
  );
}