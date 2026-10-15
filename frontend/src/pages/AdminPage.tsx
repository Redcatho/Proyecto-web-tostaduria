import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "../api/client";
import type { CreditApplication, User } from "../types";

export function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [applications, setApplications] = useState<CreditApplication[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [userResult, creditResult] = await Promise.all([
      apiRequest<{ users: User[] }>("/api/admin/users"),
      apiRequest<{ applications: CreditApplication[] }>("/api/admin/credit-applications"),
    ]);
    setUsers(userResult.users);
    setApplications(creditResult.applications);
  }

  useEffect(() => { load().catch(() => setError("No fue posible cargar administración.")); }, []);

  async function createStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await apiRequest("/api/admin/users", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
      event.currentTarget.reset();
      await load();
      setMessage("Cuenta de empleado creada.");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "No fue posible crear la cuenta."); }
  }

  async function setStatus(user: User) {
    try {
      await apiRequest(`/api/admin/users/${user.id}/status`, { method: "PATCH", body: JSON.stringify({ is_active: !user.is_active }) });
      await load();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "No fue posible actualizar la cuenta."); }
  }

  async function review(application: CreditApplication, decision: "approved" | "rejected") {
    const paymentDays = decision === "approved" ? window.prompt("Plazo aprobado (7, 15 o 30 días)", String(application.requested_days)) : null;
    const limit = decision === "approved" ? window.prompt("Límite aprobado en USD", application.requested_limit_usd) : null;
    if (decision === "approved" && (!paymentDays || !limit)) return;
    try {
      await apiRequest(`/api/admin/credit-applications/${application.id}`, {
        method: "PATCH",
        body: JSON.stringify({ decision, payment_days: Number(paymentDays), credit_limit_usd: limit, review_note: "Revisado por administración" }),
      });
      await load();
      setMessage(`Solicitud ${decision === "approved" ? "aprobada" : "rechazada"}.`);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "No fue posible revisar la solicitud."); }
  }

  return <main className="app-shell"><section className="page-header"><p className="eyebrow">Administración</p><h1>Equipo y crédito</h1></section>
    {message && <p className="notice">{message}</p>}{error && <p className="form-error">{error}</p>}
    <div className="grid admin-grid">
      <form className="card form" onSubmit={createStaff}><h2>Crear cuenta interna</h2><label>Nombre<input name="full_name" required /></label><label>Correo<input name="email" type="email" required /></label><label>Teléfono<input name="phone" /></label><label>Rol<select name="role" defaultValue="operator"><option value="operator">Operador de planta</option><option value="sales">Ventas</option><option value="dispatch">Despacho</option><option value="admin">Administración</option></select></label><label>Contraseña temporal<input name="password" type="password" minLength={6} required /></label><button>Crear empleado</button></form>
      <section className="card"><h2>Usuarios</h2><div className="table-wrap"><table><thead><tr><th>Nombre</th><th>Rol</th><th>Estado</th><th /></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.full_name}<small>{user.email}</small></td><td>{user.roles.join(", ")}</td><td>{user.is_active ? "Activo" : "Suspendido"}</td><td><button className="secondary" onClick={() => setStatus(user)}>{user.is_active ? "Suspender" : "Activar"}</button></td></tr>)}</tbody></table></div></section>
      <section className="card wide"><h2>Solicitudes de crédito</h2>{applications.length === 0 ? <p className="hint">No hay solicitudes todavía.</p> : <div className="table-wrap"><table><thead><tr><th>Empresa</th><th>Solicitud</th><th>Estado</th><th /></tr></thead><tbody>{applications.map((application) => <tr key={application.id}><td>{application.business_name ?? `Empresa #${application.business_id}`}</td><td>USD {application.requested_limit_usd}<small>{application.requested_days} días</small></td><td>{application.status}</td><td>{application.status === "pending" && <><button onClick={() => review(application, "approved")}>Aprobar</button><button className="secondary" onClick={() => review(application, "rejected")}>Rechazar</button></>}</td></tr>)}</tbody></table></div>}</section>
    </div>
  </main>;
}
