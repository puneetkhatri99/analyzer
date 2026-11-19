const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const int = new Intl.NumberFormat("en-US");

export const money = (n) => (n == null ? "—" : usd.format(n));
export const count = (n) => (n == null ? "—" : int.format(n));
export const moneyShort = (n) => (n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`);
export const range = (lo, hi) => (lo == null || hi == null ? "—" : `${money(lo)}–${money(hi)}`);
export const percent = (part, whole) => (whole ? `${Math.round((part / whole) * 100)}%` : "—");

// Pay as the posting listed it: "$17–$22 /hr" or "$45,000–$60,000"
export function listedPay(d) {
  if (d.salary_min == null || d.salary_max == null) return null;
  const amount = d.salary_min === d.salary_max ? money(d.salary_min) : `${money(d.salary_min)}–${money(d.salary_max)}`;
  return { amount, unit: d.salary_period === "hour" ? "/hr" : "/yr" };
}

export function isoDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

// The calendar day of a date or timestamp: "Nov 10, 2026" (admin) or, with month "long", "November 10, 2026".
export function longDate(value, month = "short", empty = "—") {
  const d = new Date(`${String(value || "").slice(0, 10)}T00:00:00`);
  return isNaN(d) ? empty : d.toLocaleDateString("en-US", { day: "numeric", month, year: "numeric" });
}

// "Nov 10, 3:04 PM": a recent moment, for logs.
export const when = (t) => new Date(t).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

// How a posting arrived (the API's `origin`).
export const ORIGINS = {
  feed: "JSON feed",
  excel: "Excel import",
  admin_page: "Admin · from page",
  admin_web_search: "Admin · via web search",
  collector: "Auto-collected",
};
// The "Added via" filter groups both admin origins under one choice (the API's origin=admin).
export const ORIGIN_FILTERS = { feed: ORIGINS.feed, excel: ORIGINS.excel, admin: "Added by admin", collector: ORIGINS.collector };

// Rows with fewer paid postings than this are listed but not benchmarked.
export const MIN_PAID = 5;

// "November 10, 2026" for the public pages; "…" while loading.
export const longDay = (value) => longDate(value, "long", "…");
