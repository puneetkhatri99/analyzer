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

export function longDate(value) {
  if (!value) return "—";
  const d = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return isNaN(d) ? "—" : d.toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" });
}

// Rows with fewer paid postings than this are listed but not benchmarked.
export const MIN_PAID = 5;
