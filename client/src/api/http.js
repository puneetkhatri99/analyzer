// The one place that talks HTTP. Empty base = same address as the page (FastAPI serves the app).
const API_BASE = import.meta.env.VITE_API_BASE || "";

// Drops empty values, so a filter left at "any" is not sent.
export function toQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined && v !== 0 && v !== false) q.set(k, v);
  });
  return q.toString();
}

async function request(path, { method = "GET", body, keepalive } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    keepalive,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
    error.status = res.status;
    // the session expired mid-use: reloading shows the sign-in screen (fetchMe answers null there, so no loop).
    // login and password also answer 401 for a wrong password, which is not an expired session.
    if (res.status === 401 && !["/api/admin/me", "/api/admin/login", "/api/admin/password"].includes(path)) window.location.reload();
    throw error;
  }
  return data;
}

export const getJSON = (path) => request(path);
export const postJSON = (path, body = {}) => request(path, { method: "POST", body });
export const patchJSON = (path, body) => request(path, { method: "PATCH", body });
export const del = (path) => request(path, { method: "DELETE" });
// Fire and forget, and still sent when the page is closing (a click on a link that leaves the site).
export const beacon = (path, body) => request(path, { method: "POST", body, keepalive: true }).catch(() => {});
