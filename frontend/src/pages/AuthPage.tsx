import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../api/client";
import type { User } from "../types";

type Props = { mode: "login" | "register"; onAuthenticated: (user: User) => void };

export function AuthPage({ mode, onAuthenticated }: Props) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const payload = mode === "login"
        ? { email: form.get("email"), password: form.get("password") }
        : { email: form.get("email"), full_name: form.get("full_name"), phone: form.get("phone"), password: form.get("password") };
      const response = await apiRequest<{ user: User }>(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      onAuthenticated(response.user);
      navigate("/");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No fue posible continuar.");
    } finally {
      setPending(false);
    }
  }

  const isLogin = mode === "login";
  return (
    <main className="auth-shell">
      <form className="card form" onSubmit={submit}>
        <p className="eyebrow">Tostaduria · Acceso B2B</p>
        <h1>{isLogin ? "Ingresa a tu cuenta" : "Crea tu cuenta comercial"}</h1>
        {!isLogin && <label>Nombre completo<input name="full_name" required maxLength={160} /></label>}
        {!isLogin && <label>Teléfono<input name="phone" maxLength={40} /></label>}
        <label>Correo electrónico<input name="email" type="email" required /></label>
        <label>Contraseña<input name="password" type="password" required minLength={6} /></label>
        {!isLogin && <p className="hint">Usa al menos 6 caracteres.</p>}
        {error && <p className="form-error">{error}</p>}
        <button disabled={pending}>{pending ? "Procesando..." : isLogin ? "Ingresar" : "Crear cuenta"}</button>
        <p className="hint">
          {isLogin ? "¿No tienes cuenta?" : "¿Ya tienes cuenta?"} {" "}
          <Link to={isLogin ? "/registro" : "/ingresar"}>{isLogin ? "Regístrate" : "Ingresa"}</Link>
        </p>
      </form>
    </main>
  );
}
