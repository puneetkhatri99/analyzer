import { useEffect, useRef, useState } from "react";
import { fetchReport, reportQuery } from "@/api/report.js";
import { track } from "@/features/site/lead.js";
import { filtersFromUrl } from "../lib/filters.js";

// The report for the applied filters. The filter panel edits a draft; the report changes only on "Search"
// (apply) or "Reset filters" (reset), and each change goes into the lead's history with what caused it.
// Applied filters are kept in the URL; only the newest answer is shown when several are in flight.
export function useReport() {
  const [initial] = useState(filtersFromUrl); // the search the report opened with; "Reset filters" goes back to it
  const [filters, setFilters] = useState(initial);
  const [draft, setDraft] = useState(initial);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(true);
  const latest = useRef(0);
  const cause = useRef("open"); // open | update | reset, for the history

  useEffect(() => {
    const q = reportQuery(filters);
    window.history.replaceState(null, "", `/report${q ? `?${q}` : ""}`);
    const id = ++latest.current;
    const trigger = cause.current;
    setUpdating(true);
    fetchReport(filters)
      .then((r) => {
        if (id !== latest.current) return;
        setReport(r);
        setError(null);
        const chosen = Object.fromEntries(Object.entries(filters).filter(([, v]) => v?.length));
        track("report", { ...chosen, trigger, shown: `${r.title.role} in ${r.title.area}`, widened_to: r.scope === "state" ? null : r.area_name });
      })
      .catch((e) => id === latest.current && setError(e.message))
      .finally(() => id === latest.current && setUpdating(false));
  }, [filters]);

  const same = (a, b) => reportQuery(a) === reportQuery(b);
  const apply = () => { cause.current = "update"; setFilters(draft); };
  const reset = () => { cause.current = "reset"; setDraft(initial); setFilters(initial); };
  return {
    filters, draft, setDraft, apply, reset,
    pending: !same(draft, filters), // the panel has changes the report doesn't show yet
    changed: !same(draft, initial) || !same(filters, initial),
    report, error, updating,
  };
}
