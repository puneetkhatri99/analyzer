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

export const fetchSources = () => getJSON("/api/sources");
export const fetchFilterOptions = (source) => getJSON(`/api/filter-options?${toQuery({ source })}`);
export const fetchSummary = (source, filters) => getJSON(`/api/summary?${toQuery({ source, ...filters })}`);
export const fetchJobs = (source, filters) => getJSON(`/api/jobs?${toQuery({ source, ...filters })}`);
