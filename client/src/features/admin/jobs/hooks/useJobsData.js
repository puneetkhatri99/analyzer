import { useCallback, useEffect, useRef, useState } from "react";
import { fetchFilterOptions, fetchJobs, fetchSources, fetchSummary } from "@/api/admin.js";
import { toQuery } from "@/api/http.js";
import { EMPTY_FILTERS, filtersFromUrl, sourceFromUrl, toggleSource } from "../lib/filters.js";

// Everything the Jobs dashboard shows for the chosen sources (one or more) and filters. Filter changes are debounced and
// written to the URL; only the newest answer is kept when several requests overlap.
export function useJobsData() {
  const [source, setSource] = useState(sourceFromUrl);
  const [filters, setFilters] = useState(filtersFromUrl);
  const [sources, setSources] = useState(null);
  const [options, setOptions] = useState(null);
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [updating, setUpdating] = useState(true);
  const [error, setError] = useState(null);
  const latest = useRef(0);

  const reloadSources = useCallback(() => fetchSources().then(setSources).catch(() => {}), []);

  useEffect(() => {
    setOptions(null);
    fetchFilterOptions(source).then(setOptions).catch(() => {});
    reloadSources();
  }, [source, reloadSources]);

  const load = useCallback(() => {
    const id = ++latest.current;
    setUpdating(true);
    Promise.all([fetchSummary(source, filters), fetchJobs(source, filters)])
      .then(([s, j]) => {
        if (id !== latest.current) return;
        setSummary(s);
        setRows(j.rows);
        setError(null);
      })
      .catch((e) => id === latest.current && setError(e.message))
      .finally(() => id === latest.current && setUpdating(false));
  }, [source, filters]);

  useEffect(() => {
    const query = toQuery({ source: source.join(",") === "json" ? "" : source.join(","), ...filters });
    window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
    const timer = setTimeout(load, 200);
    return () => clearTimeout(timer);
  }, [source, filters, load]);

  // Filter values differ per source (roles, states, denominations), so a change starts clean.
  const changeSource = (key) => {
    const next = toggleSource(source, key);
    if (next === source) return;
    setSummary(null);
    setRows([]);
    setFilters(EMPTY_FILTERS);
    setSource(next);
  };

  return {
    source, changeSource, sources, options, summary, rows, updating, error, filters,
    setFilter: (key, value) => setFilters((f) => ({ ...f, [key]: value })),
    clearFilter: (key) => setFilters((f) => ({ ...f, [key]: EMPTY_FILTERS[key] })),
    resetFilters: () => setFilters(EMPTY_FILTERS),
    reload: () => { load(); reloadSources(); },
  };
}
