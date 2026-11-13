import { useEffect, useRef, useState } from "react";
import { fetchReport, reportQuery } from "@/api/report.js";
import { filtersFromUrl } from "../lib/filters.js";

// The report for the current filters. Filters are kept in the URL; quick changes are debounced,
// and only the newest answer is shown when several are in flight.
export function useReport() {
  const [filters, setFilters] = useState(filtersFromUrl);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(true);
  const latest = useRef(0);

  useEffect(() => {
    const q = reportQuery(filters);
    window.history.replaceState(null, "", `/report${q ? `?${q}` : ""}`);
    const id = ++latest.current;
    setUpdating(true);
    const timer = setTimeout(() => fetchReport(filters)
      .then((r) => { if (id === latest.current) { setReport(r); setError(null); } })
      .catch((e) => id === latest.current && setError(e.message))
      .finally(() => id === latest.current && setUpdating(false)), 150);
    return () => clearTimeout(timer);
  }, [filters]);

  return { filters, setFilters, report, error, updating };
}
