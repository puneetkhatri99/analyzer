import { useEffect, useState } from "react";
import { fetchReportOptions } from "@/api/report.js";

// Roles, states, sizes, denominations, job types and the landing stats. Shared by the landing and report pages.
export function useReportOptions() {
  const [options, setOptions] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetchReportOptions().then(setOptions).catch(() => setError("We couldn't load the tool. Please refresh the page."));
  }, []);
  return { options, error };
}
