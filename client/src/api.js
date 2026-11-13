// Empty = same address as the page (FastAPI serves the dashboard). Set only to call an API elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE || "";

export function toQuery(filters) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined && v !== 0 && v !== false) params.set(k, v);
  });
  return params.toString();
}

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json();
}

export async function postJSON(path, body, method = "POST") {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  return data;
}

export const fetchSources = () => getJSON("/api/sources");
export const fetchFilterOptions = (source) => getJSON(`/api/filter-options?${toQuery({ source })}`);
export const fetchSummary = (source, filters) => getJSON(`/api/summary?${toQuery({ source, ...filters })}`);
export const fetchJobs = (source, filters) => getJSON(`/api/jobs?${toQuery({ source, ...filters })}`);

// Public report. Lists go out as repeated keys: ?state=Ohio&state=Indiana
export function reportQuery(f) {
  const params = new URLSearchParams();
  for (const key of ["role", "state", "size", "denomination"]) (f[key] || []).forEach((v) => params.append(key, v));
  if (f.type && f.type !== "full-time") params.set("type", f.type);
  return params.toString();
}
export const fetchReportOptions = () => getJSON("/api/report/options");
export const fetchReport = (f) => getJSON(`/api/report?${reportQuery(f)}`);
export const postLead = (lead) => postJSON("/api/leads", lead);
