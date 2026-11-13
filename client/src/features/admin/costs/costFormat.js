export const PURPOSES = { extract: "Job extraction", church_lookup: "Church size lookup" };
export const purpose = (key) => PURPOSES[key] || key;

// AI calls cost fractions of a cent, so tiny amounts show 4 decimals.
export function usd(n) {
  const v = Number(n) || 0;
  return v > 0 && v < 1 ? `$${v.toFixed(4)}` : `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export const when = (t) => new Date(t).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
