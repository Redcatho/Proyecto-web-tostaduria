import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiRequest } from "../api/client";
import type { Business, CreditApplication, CreditTerms, User } from "../types";

type Props = { user: User; onUserUpdated: (user: User) => void };

export function ProfilePage({ user, onUserUpdated }: Props) {
  const [business, setBusiness] = useState<Business | null>(null);
  const [applications, setApplications] = useState<CreditApplication[]>([]);
  const [terms, setTerms] = useState<CreditTerms | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  async function load() {
    const [businessResult, creditResult] = await Promise.all([
      apiRequest<{ business: Business | null }>("/api/businesses/me"),
      apiRequest<{ applications: CreditApplication[]; active_terms: CreditTerms | null }>("/api/credit-applications/me"),
    ]);
    setBusiness(businessResult.business);
    setApplications(creditResult.applications);
    setTerms(creditResult.active_terms);
  }

  useEffect(() => { load().catch(() => setError("No fue posible cargar tu perfil.")); }, []);

  function showToast(text: string) {
    setToast(text);
    window.setTimeout(() => setToast(""), 3500);
  }

  async function savePersonal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiRequest<{ user: User }>("/api/auth/me", { method: "PATCH", body: JSON.stringify({ full_name: form.get("full_name"), phone: form.get("phone") }) });
      onUserUpdated(result.user);
      setMessage("Datos personales actualizados.");
      showToast("Contacto guardado ✓");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Error al guardar."); }
  }

  async function saveBusiness(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiRequest<{ business: Business }>("/api/businesses/me", {
        method: "PATCH",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      setBusiness(result.business);
      setMessage("Perfil de empresa guardado.");
      showToast(result.business.profile_status === "complete" ? "Perfil completo ✓" : "Perfil guardado — falta algo para completar");
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Error al guardar."); }
  }

  async function addAddress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await apiRequest<{ address: { id: number } }>("/api/businesses/me/addresses", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
      await load();
      setMessage("Dirección agregada.");
      showToast("Dirección guardada ✓");
      event.currentTarget.reset();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Error al guardar."); }
  }

  async function requestCredit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/api/credit-applications", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
      await load();
      setMessage("Solicitud de crédito enviada a administración.");
      showToast("Crédito solicitado ✓");
      event.currentTarget.reset();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Error al enviar."); }
  }

  const complete = business?.profile_status === "complete";
  return <main className="app-shell"><section className="page-header"><p className="eyebrow">Mi cuenta</p><h1>Perfil comercial</h1></section>
    {toast && <div className="profile-toast">{toast}</div>}
    {message && <p className="notice">{message}</p>}{error && <p className="form-error">{error}</p>}
    <section className="card"><h2>Estado del perfil</h2>{complete ? <p className="profile-status profile-status--ok">✓ Perfil completo</p> : <><p className="profile-status">Perfil incompleto — falta completar campos o agregar una dirección</p><p className="hint">Para solicitar crédito y cotizar, completa la empresa y agrega al menos una dirección.</p></>}</section>
    <div className="grid">
      <form className="card form" onSubmit={savePersonal}><h2>Contacto</h2><label>Nombre<input name="full_name" defaultValue={user.full_name} required /></label><label>Teléfono<input name="phone" defaultValue={user.phone ?? ""} /></label><button>Guardar contacto</button></form>
      <form className="card form" onSubmit={saveBusiness}><h2>Empresa</h2><label>Nombre comercial<input name="legal_name" defaultValue={business?.legal_name ?? ""} required /></label><label>RIF o cédula<input name="tax_id" defaultValue={business?.tax_id ?? ""} required /></label><label>Tipo de negocio<select name="business_type" defaultValue={business?.business_type ?? ""} required><option value="">Selecciona</option><option value="cafeteria">Cafetería</option><option value="supermarket">Supermercado</option><option value="wholesaler">Mayorista</option></select></label><label>Responsable<input name="contact_name" defaultValue={business?.contact_name ?? user.full_name} required /></label><label>Correo de contacto<input name="contact_email" type="email" defaultValue={business?.contact_email ?? user.email} required /></label><label>Teléfono de contacto<input name="contact_phone" defaultValue={business?.contact_phone ?? user.phone ?? ""} /></label><button>Guardar empresa</button></form>
      <form className="card form" onSubmit={addAddress}><h2>Dirección</h2><label>Dirección<input name="line1" required /></label><label>Ciudad<input name="city" required /></label><label>Estado<input name="state" required /></label><label>Etiqueta<input name="label" defaultValue="Principal" /></label><button>Agregar dirección</button>{business?.addresses.map((address) => <p className="hint" key={address.id}>{address.label}: {address.line1}, {address.city}, {address.state}</p>)}</form>
      <section className="card"><h2>Crédito comercial</h2>{terms ? <p className="notice">Activo: USD {terms.credit_limit_usd} · {terms.payment_days} días</p> : <p className="hint">No tienes crédito activo.</p>}<form className="form" onSubmit={requestCredit}><label>Plazo solicitado<select name="requested_days" defaultValue=""><option value="" disabled>Selecciona</option><option value="7">7 días</option><option value="15">15 días</option><option value="30">30 días</option></select></label><label>Límite solicitado (USD)<input name="requested_limit_usd" type="number" min="1" step="0.01" required /></label><label>Justificación<textarea name="justification" maxLength={1000} /></label><button disabled={!complete}>Solicitar crédito</button>{!complete && <p className="hint">Completa tu perfil de empresa y agrega una dirección primero.</p>}</form>{applications.map((application) => <p className="hint" key={application.id}>Solicitud #{application.id}: {application.status} · USD {application.requested_limit_usd}</p>)}</section>
    </div>
  </main>;
}