// The report's filters live in the URL, so a report can be bookmarked or shared.
export const LISTS = ["role", "state", "size", "denomination"];
export const FULL_TIME = "full-time";
export const PART_TIME = "part-time";

export function filtersFromUrl(search = window.location.search) {
  const p = new URLSearchParams(search);
  const f = Object.fromEntries(LISTS.map((k) => [k, p.getAll(k)]));
  f.type = p.get("type") === PART_TIME ? PART_TIME : FULL_TIME;
  return f;
}

// One line for the folded filter panel on phones: "Worship/Music · Ohio · Full-time"
export function activeSummary(f, jobTypes) {
  const type = jobTypes.find((t) => t.key === f.type)?.label;
  return [...f.role, ...f.state, ...f.size, ...f.denomination, type].filter(Boolean).join(" · ");
}
