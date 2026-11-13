import { money } from "../../../lib/format.js"; // relative so node --test can run it

// Full-time pay is yearly, part-time is an hourly rate.
export const pay = (v, unit) => (v == null ? "—" : unit === "hour" ? `$${v.toFixed(2)}` : money(v));
export const per = (unit) => (unit === "hour" ? "/ hour" : "/ year");

// Where a planned offer lands against current openings: [headline, sentence].
export function offerVerdict(amount, p, unit) {
  const a = pay(amount, unit);
  if (amount < p.low) return ["Below market.", `${a} is below the lower quarter of current openings, so expect fewer strong candidates.`];
  if (amount < p.typical) return ["Within range.", `${a} sits between the lower quarter and typical pay of current openings.`];
  if (amount <= p.high) return ["Competitive.", `${a} sits above typical pay and below the upper quarter of current openings.`];
  return ["Above market.", `${a} is above the upper quarter of current openings.`];
}

// Reads "52,000", "$18.50" or "18.5" as a number; null when it isn't one.
export function parseAmount(text) {
  const n = parseFloat(String(text).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) && n > 0 ? n : null;
}

// Where a value sits on the range bar, as a % of its width. The bar runs a little past both quarters.
export function rangeScale(p) {
  const spread = Math.max(p.high - p.low, p.typical * 0.1);
  const lo = p.low - spread * 0.35;
  const hi = p.high + spread * 0.35;
  return (v) => `${Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100))}%`;
}
