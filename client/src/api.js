const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

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

export const fetchFilterOptions = () => getJSON("/api/filter-options");
export const fetchSummary = (filters) => getJSON(`/api/summary?${toQuery(filters)}`);
export const fetchJobs = (filters) => getJSON(`/api/jobs?${toQuery(filters)}`);
