// The All leads table's filters. Every lead is already loaded, so filtering happens here, in the browser.

export const ANY = "any"; // Radix Select can't hold "", so "any" means no filter
const DAY = 864e5;

// report_email is the latest "Email me this report" outcome: sent / failed / skipped, null if never asked.
export const SHOW = {
  all: ["All leads", () => true],
  hot: ["Hot leads", (l) => l.hot],
  booked: ["Booked a call", (l) => l.booked],
  emailed: ["Report emailed", (l) => l.report_email === "sent"],
  email_failed: ["Email not sent", (l) => l.report_email === "failed" || l.report_email === "skipped"],
};

export const SINCE = { [ANY]: ["Any time", 0], week: ["Last 7 days", 7], month: ["Last 30 days", 30], quarter: ["Last 90 days", 90] };

export const NO_FILTERS = { query: "", show: "all", role: ANY, location: ANY, since: ANY };

export const isFiltered = (f) => Object.keys(NO_FILTERS).some((k) => (k === "query" ? f.query.trim() : f[k] !== NO_FILTERS[k]));

// The distinct values of one field, for a filter's choices.
export const choices = (leads, key) => [...new Set(leads.map((l) => l[key]).filter(Boolean))].sort();

export function filterLeads(leads, f, now = Date.now()) {
  const q = f.query.trim().toLowerCase();
  const days = SINCE[f.since][1];
  return leads.filter((l) =>
    SHOW[f.show][1](l)
    && (f.role === ANY || l.role === f.role)
    && (f.location === ANY || l.location === f.location)
    && (!days || Date.parse(l.created_at) >= now - days * DAY)
    && (!q || [l.name, l.email, l.organization, l.role, l.location].some((v) => v?.toLowerCase().includes(q))));
}
