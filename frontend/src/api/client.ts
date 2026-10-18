const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:5000";
const TOKEN_KEY = "tostaduria_access_token";

let _onUnauthorized: (() => void) | null = null;
let _token: string | null = localStorage.getItem(TOKEN_KEY);

export function setAccessToken(token: string) {
  _token = token;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  _token = null;
  localStorage.removeItem(TOKEN_KEY);
}

export function setOnUnauthorized(cb: () => void) {
  _onUnauthorized = cb;
}

export type ApiHealth = {
  status: "ok";
  database: "ok";
  timestamp: string;
};

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_access_token="))
    ?.split("=")[1];
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const method = options.method?.toUpperCase() ?? "GET";
  if (_token) headers.set("Authorization", "Bearer " + _token);
  if (options.body) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = csrfToken();
    if (csrf) headers.set("X-CSRF-TOKEN", csrf);
  }
  const response = await fetch(`${apiUrl}${path}`, { ...options, headers, credentials: "include" });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && _onUnauthorized && path !== "/api/auth/login" && path !== "/api/auth/register") {
    _onUnauthorized();
  }
  if (response.status === 401 && _onUnauthorized && path != "/api/auth/login" && path != "/api/auth/register") {
    _onUnauthorized();
  }
  if (!response.ok) {
    throw new ApiError(data.error?.message ?? "No fue posible completar la solicitud.", response.status);
  }
  return data as T;
}

export async function apiDownload(path: string): Promise<Blob> {
  const response = await fetch(`${apiUrl}${path}`, { credentials: "include" });
  if (response.status === 401 && _onUnauthorized && path != "/api/auth/login" && path != "/api/auth/register") {
    _onUnauthorized();
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.error?.message ?? "No fue posible descargar el documento.", response.status);
  }
  return response.blob();
}

export async function getApiHealth(signal?: AbortSignal): Promise<ApiHealth> {
  return apiRequest<ApiHealth>("/api/health", { signal });
}
