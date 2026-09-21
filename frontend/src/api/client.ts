// Same-origin deployments (nginx reverse proxy, or the Vite dev proxy in
// vite.config.ts) work with the default "/api" — the request stays on
// whatever domain served the page. Split deployments (frontend and
// backend on two different hosts, e.g. a static site + a separate API
// service) need this pointed at the backend's full URL instead, set at
// build time via VITE_API_BASE_URL (see .env.example / DEPLOYMENT.md).
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

const TOKEN_KEY = "report_validator_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 204) return undefined as T;

  const isJson = resp.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await resp.json() : await resp.text();

  if (!resp.ok) {
    throw new ApiError(resp.status, isJson ? payload.detail ?? payload : payload);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// Export/file endpoints require the Authorization header, which a plain
// <a href> cannot send, so downloads go through fetch + a Blob object URL.
export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const resp = await fetch(`${API_BASE}${path}`, { headers });
  if (!resp.ok) throw new ApiError(resp.status, await resp.text());
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
