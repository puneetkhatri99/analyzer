// Public report API: summary figures only, no counts, employers or links.
import { LISTS } from "@/features/report/lib/filters.js";
import { getJSON, postJSON } from "./http.js";

// Lists go out as repeated keys: ?state=Ohio&state=Indiana. Full-time is the default and is left out.
export function reportQuery(f) {
  const q = new URLSearchParams();
  for (const key of LISTS) (f[key] || []).forEach((v) => q.append(key, v));
  if (f.type && f.type !== "full-time") q.set("type", f.type);
  return q.toString();
}

export const fetchReportOptions = () => getJSON("/api/report/options");
export const fetchReport = (f) => getJSON(`/api/report?${reportQuery(f)}`);
export const postLead = (lead) => postJSON("/api/leads", lead);
