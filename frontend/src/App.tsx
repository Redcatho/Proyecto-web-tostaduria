import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { apiRequest, getApiHealth } from "./api/client";
import { AuthPage } from "./pages/AuthPage";
import { AdminPage } from "./pages/AdminPage";
import { CatalogAdminPage } from "./pages/CatalogAdminPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CartPage, QuotePage } from "./pages/CartPage";
import { QuoteDetailPage } from "./pages/QuoteDetailPage";
import { ProfilePage } from "./pages/ProfilePage";
import { OrderDetailPage, OrdersPage } from "./pages/OrdersPage";
import { OperationsPage } from "./pages/OperationsPage";
import type { ExchangeRate, User } from "./types";

type HealthState = "loading" | "online" | "offline";

function PlatformStatus() {
  const [status, setStatus] = useState<HealthState>("loading");

  useEffect(() => {
    const controller = new AbortController();
    getApiHealth(controller.signal)
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));

    return () => controller.abort();
  }, []);

  const label = {
    loading: "Verificando API",
    online: "Infraestructura conectada",
    offline: "API no disponible",
  }[status];

  return (
    <main className="shell">
      <section className="hero" aria-labelledby="platform-title">
        <p className="eyebrow">Tostaduria · Plataforma B2B</p>
        <h1 id="platform-title">La base operativa esta lista.</h1>
        <p className="summary">
          El catalogo, pedidos, produccion y comunicaciones se incorporaran en las siguientes fases.
        </p>
        <p className={`status status--${status}`} role="status">
          <span aria-hidden="true" />
          {label}
        </p>
      </section>
    </main>
  );
}

function Dashboard({ user, rate }: { user: User; rate: ExchangeRate | null }) {
  return <main className="app-shell"><section className="hero"><p className="eyebrow">Tostaduria · Portal B2B</p><h1>Hola, {user.full_name.split(" ")[0]}.</h1>{rate && <div className="rate-card"><p className="rate-note">💱 Tasa BCV: 1 USD = <strong>Bs. {rate.rate_ves}</strong> · {rate.effective_date}</p></div>}<p className="summary">Tu cuenta está lista. Completa tu perfil comercial y solicita condiciones de crédito cuando tu empresa lo necesite.</p><Link className="button-link" to="/perfil">Completar perfil</Link></section></main>;
}

function Navigation({ user, cartCount, onLogout }: { user: User; cartCount: number; onLogout: () => void }) {
  return <header className="topbar"><Link to="/">Tostaduria</Link><nav><Link to="/catalogo">Catálogo</Link><Link to="/carrito">Carrito{cartCount > 0 && <span className="cart-badge">{cartCount}</span>}</Link><Link to="/pedidos">Mis pedidos</Link><Link to="/perfil">Mi perfil</Link>{user.roles.includes("admin") && <Link to="/administracion">Administración</Link>}{user.roles.some((role) => ["admin", "operator", "dispatch", "sales"].includes(role)) && <Link to="/operacion/pedidos">Operación</Link>}<button className="text-button" onClick={onLogout}>Salir</button></nav></header>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [cartCount, setCartCount] = useState<number>(0);
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    apiRequest<{ user: User }>("/api/auth/me")
      .then((result) => setUser(result.user))
      .catch(() => setUser(null))
      .finally(() => setLoadingSession(false));
  }, []);

  useEffect(() => {
    apiRequest<{ exchange_rate: ExchangeRate | null }>("/api/catalog/exchange-rates/current")
      .then((result) => setRate(result.exchange_rate))
      .catch(() => setRate(null));
  }, []);

  useEffect(() => {
    if (user) {
      apiRequest<{ count: number }>("/api/cart/count")
        .then((result) => setCartCount(result.count))
        .catch(() => setCartCount(0));
    } else { setCartCount(0); }
  }, [user]);

  function refreshCartCount() {
    if (user) { apiRequest<{ count: number }>("/api/cart/count").then((result) => setCartCount(result.count)).catch(() => {}); }
  }

  async function logout() {
    try { await apiRequest("/api/auth/logout", { method: "POST" }); } finally { setUser(null); setCartCount(0); navigate("/ingresar"); }
  }

  if (loadingSession) return <PlatformStatus />;
  return (
    <>{user && <Navigation user={user} cartCount={cartCount} onLogout={logout} />}<Routes>
      <Route path="/ingresar" element={user ? <Navigate to="/" replace /> : <AuthPage mode="login" onAuthenticated={setUser} />} />
      <Route path="/registro" element={user ? <Navigate to="/" replace /> : <AuthPage mode="register" onAuthenticated={setUser} />} />
      <Route path="/" element={user ? <Dashboard user={user} rate={rate} /> : <CatalogPage onCartUpdate={refreshCartCount} />} />
      <Route path="/catalogo" element={<CatalogPage authenticated={Boolean(user)} onCartUpdate={refreshCartCount} />} />
      <Route path="/carrito" element={user ? <CartPage /> : <Navigate to="/ingresar" replace />} />
      <Route path="/cotizar" element={user ? <QuotePage /> : <Navigate to="/ingresar" replace />} />
      <Route path="/cotizaciones/:id" element={user ? <QuoteDetailPage /> : <Navigate to="/ingresar" replace />} />
      <Route path="/pedidos" element={user ? <OrdersPage /> : <Navigate to="/ingresar" replace />} />
      <Route path="/pedidos/:id" element={user ? <OrderDetailPage /> : <Navigate to="/ingresar" replace />} />
      <Route path="/perfil" element={user ? <ProfilePage user={user} onUserUpdated={setUser} /> : <Navigate to="/ingresar" replace />} />
      <Route path="/administracion" element={user?.roles.includes("admin") ? <AdminPage /> : <Navigate to="/" replace />} />
      <Route path="/operacion" element={user?.roles.some((role) => ["admin", "operator", "sales"].includes(role)) ? <CatalogAdminPage /> : <Navigate to="/" replace />} />
      <Route path="/operacion/pedidos" element={user?.roles.some((role) => ["admin", "operator", "dispatch", "sales"].includes(role)) ? <OperationsPage user={user} /> : <Navigate to="/" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></>
  );
}
