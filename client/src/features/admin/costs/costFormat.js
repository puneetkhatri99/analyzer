// What the AI was doing, in plain words (the keys are the "purpose" the server records with each call).
export const PURPOSES = {
  extract: "Adding a job from a link",
  church_lookup: "Looking up a church’s size and group",
  pay_extract: "Reading pay from a job posting",
  posting_review: "Checking a new job and its pay",
  bizdev_pay: "Finding pay for an Excel job",
};
export const purpose = (key) => PURPOSES[key] || key;

// An automatic run's ID ("feed-20261118-101601", "bizdev-20261119-110406") as a name: what ran.
export function runName(id) {
  if (id?.startsWith("feed-")) return "Daily church jobs download";
  if (id?.startsWith("bizdev-trial-")) return "Excel sheets AI trial";
  if (id?.startsWith("bizdev-")) return "Excel sheets AI fill-in";
  return id;
}

// AI calls cost fractions of a cent, so tiny amounts show 4 decimals.
export function usd(n) {
  const v = Number(n) || 0;
  return v > 0 && v < 1 ? `$${v.toFixed(4)}` : `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
