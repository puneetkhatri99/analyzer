// The Jobs dashboard's source and filters, kept in the URL so a view can be bookmarked or shared.
export const SOURCES = ["json", "churches", "nonprofits"];

export const EMPTY_FILTERS = {
  search: "", role: "", region: "", denomination: "", min_church_size: 0, hours: "", origin: "",
  country: "", remote: "", min_salary: 0, has_pay: false,
};

export const isSet = (v) => v !== "" && v !== 0 && v !== false && v != null;

// One source or several ("json,churches"), in SOURCES order; the feed when none is valid.
export function sourceFromUrl(search = window.location.search) {
  const picked = (new URLSearchParams(search).get("source") || "").split(",");
  const valid = SOURCES.filter((s) => picked.includes(s));
  return valid.length ? valid : ["json"];
}

// Add or remove one source; the last one can't be removed.
export function toggleSource(chosen, key) {
  const next = SOURCES.filter((s) => (s === key ? !chosen.includes(s) : chosen.includes(s)));
  return next.length ? next : chosen;
}

// Each value keeps the type of its empty default: numbers, booleans or text.
export function filtersFromUrl(search = window.location.search) {
  const params = new URLSearchParams(search);
  const f = { ...EMPTY_FILTERS };
  for (const key of Object.keys(f)) {
    if (!params.has(key)) continue;
    const raw = params.get(key);
    if (typeof f[key] === "number") f[key] = Number(raw) || 0;
    else if (typeof f[key] === "boolean") f[key] = raw === "true";
    else f[key] = raw;
  }
  return f;
}
