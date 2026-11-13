import React, { useCallback, useEffect, useRef, useState } from "react";
import FilterBar from "./components/FilterBar.jsx";
import KpiStrip from "./components/KpiStrip.jsx";
import PayLadder from "./components/PayLadder.jsx";
import BreakdownList from "./components/BreakdownList.jsx";
import PayDistribution from "./components/PayDistribution.jsx";
import JobsTable, { CSV_COLUMNS } from "./components/JobsTable.jsx";
import { downloadCsv, toCsv } from "./csv.js";
import SourceTabs from "./components/SourceTabs.jsx";
import JobDetail from "./components/JobDetail.jsx";
import { fetchFilterOptions, fetchJobs, fetchSources, fetchSummary, postJSON, toQuery } from "./api.js";
import { MIN_PAID, count, longDate, money } from "./format.js";
import { Download } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const EMPTY_FILTERS = {
  search: "", role: "", region: "", denomination: "", min_church_size: 0, hours: "", status: "", origin: "",
  country: "", remote: "", min_salary: 0, has_pay: false,
};

const SOURCES = ["json", "churches", "nonprofits"];

function sourceFromUrl() {
  const s = new URLSearchParams(window.location.search).get("source");
  return SOURCES.includes(s) ? s : "json";
}

function filtersFromUrl() {
  const params = new URLSearchParams(window.location.search);
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

function finding(filters, stats) {
  const subject = filters.role || "all roles";
  const where = filters.region ? ` in ${filters.region}` : "";
  const others = Object.entries(filters).some(([k, v]) => !["role", "region"].includes(k) && v !== "" && v !== 0 && v !== false);
  const scope = `${subject}${where}${others ? " matching your filters" : ""}`;
  const unpaid = stats.postings - stats.paid;

  if (stats.postings === 0) return <>No postings match these filters.</>;
  if (stats.paid < MIN_PAID) {
    return <>Only {count(stats.paid)} of {count(stats.postings)} postings for {scope} list pay, too few to benchmark. Widen the filters to compare.</>;
  }
  return (
    <>
      Median listed pay for {scope} is <strong>{money(stats.median)} a year</strong>, from {count(stats.paid)} postings that state it.
      {unpaid > 0 && <> {count(unpaid)} of {count(stats.postings)} postings list no pay at all.</>}
    </>
  );
}

function LoadingCard({ className, title, rows = 6 }) {
  return (
    <Card className={className} aria-busy="true">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-8 items-center">
          <Skeleton className="h-2.5" style={{ width: `${90 - i * 8}%` }} />
        </div>
      ))}
    </Card>
  );
}

// Admin only (brief A1, A2): the per-source view with every posting, its source and its link.
export default function AdminJobs({ canEdit = false }) {
  const [source, setSource] = useState(sourceFromUrl);
  const [sources, setSources] = useState(null);
  const [filters, setFilters] = useState(filtersFromUrl);
  const [options, setOptions] = useState(null);
  const [summary, setSummary] = useState(null);
  const [rows, setRows] = useState([]);
  const [updating, setUpdating] = useState(true);
  const [error, setError] = useState(null);
  const [table, setTable] = useState(null);
  const [openJob, setOpenJob] = useState(null);
  const requestId = useRef(0);

  useEffect(() => {
    setOptions(null);
    fetchFilterOptions(source).then(setOptions).catch(() => {});
    fetchSources().then(setSources).catch(() => {});
  }, [source]);

  const load = useCallback((src, f) => {
    const id = ++requestId.current;
    setUpdating(true);
    Promise.all([fetchSummary(src, f), fetchJobs(src, f)])
      .then(([s, j]) => {
        if (id !== requestId.current) return;
        setSummary(s);
        setRows(j.rows);
        setError(null);
      })
      .catch((e) => id === requestId.current && setError(e.message))
      .finally(() => id === requestId.current && setUpdating(false));
  }, []);

  useEffect(() => {
    const query = toQuery({ source: source === "json" ? "" : source, ...filters });
    window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
    const timer = setTimeout(() => load(source, filters), 200);
    return () => clearTimeout(timer);
  }, [source, filters, load]);

  // Filter values differ per source (roles, states, denominations), so a switch starts clean.
  const changeSource = (next) => {
    setSummary(null);
    setRows([]);
    setFilters(EMPTY_FILTERS);
    setSource(next);
  };

  const setFilter = (key, value) => setFilters((f) => ({ ...f, [key]: value }));
  const clearFilter = (key) => setFilter(key, EMPTY_FILTERS[key]);
  const resetFilters = () => setFilters(EMPTY_FILTERS);
  // exports every matching posting, in the table's current sort order
  const exportCsv = () => downloadCsv(toCsv(table.getSortedRowModel().rows.map((r) => r.original), CSV_COLUMNS),
    `ministry-jobs-${source}-${new Date().toISOString().slice(0, 10)}.csv`);

  const s = summary?.stats;
  const current = sources?.find((x) => x.key === source);
  const isChurch = source !== "nonprofits";

  return (
    <>
        <SourceTabs sources={sources} value={source} onChange={changeSource} />

        <div className="title-row">
          <div>
            <h1>Jobs by source</h1>
            <p className="muted small">{current?.label || "…"} · {source === "json" ? "data as of" : "pages last read"} {s?.as_of ? longDate(s.as_of) : "…"}</p>
            <p className="finding" aria-live="polite">
              {s ? finding(filters, s) : <Skeleton className="inline-block h-4 w-[min(520px,100%)]" />}
            </p>
          </div>
          <Button onClick={exportCsv} disabled={!table || !s?.postings}>
            <Download aria-hidden="true" />
            Export {s ? count(s.postings) : ""} postings
          </Button>
        </div>

        <FilterBar filters={filters} setFilter={setFilter} clearFilter={clearFilter} resetFilters={resetFilters} options={options} showChurchSize={isChurch} />

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Couldn’t load the benchmarks.</AlertTitle>
            <AlertDescription>
              The server didn’t answer ({error}). It may be waking up; try again in a minute.
              <Button variant="outline" size="sm" className="mt-2 text-foreground" onClick={() => load(source, filters)}>Retry</Button>
            </AlertDescription>
          </Alert>
        )}

        {!error && (
          <div className={`dash-grid${updating && summary ? " is-updating" : ""}`} aria-busy={updating}>
            <div className="span-12"><KpiStrip stats={s} loading={!s} /></div>

            {!summary ? (
              <>
                <LoadingCard className="span-7" title="Pay by role" rows={12} />
                <LoadingCard className="span-5" title="Pay by state" rows={12} />
              </>
            ) : (
              <>
                <Card as="section" className="span-7" aria-labelledby="h-role">
                  <CardHeader>
                    <CardTitle id="h-role">Pay by role</CardTitle>
                    <div className="legend" aria-hidden="true">
                      <span><i className="sw-band" />Middle half</span>
                      <span><i className="sw-tick" />Median</span>
                    </div>
                  </CardHeader>
                  <PayLadder rows={summary.by_role} nameHeader="Role" selected={filters.role} onSelect={(v) => setFilter("role", v)} />
                  <p className="card-note">Annual pay; hourly roles counted at 2,080 hours. Role is matched from the job title. Roles with fewer than {MIN_PAID} paid postings aren’t benchmarked.</p>
                </Card>

                <div className="stack span-5">
                  <Card as="section" aria-labelledby="h-state">
                    <CardHeader>
                      <CardTitle id="h-state">Pay by state</CardTitle>
                      <CardDescription>Top 10 by postings</CardDescription>
                    </CardHeader>
                    <PayLadder compact rows={summary.by_state} nameHeader="State" selected={filters.region} onSelect={(v) => setFilter("region", v)} />
                  </Card>

                  {isChurch && <Card as="section" aria-labelledby="h-size">
                    <CardHeader>
                      <CardTitle id="h-size">By church size</CardTitle>
                      <CardDescription>Weekly attendance</CardDescription>
                    </CardHeader>
                    <BreakdownList rows={summary.by_church_size.filter((r) => r.postings > 0)} nameHeader="Attendance" />
                    <p className="card-note">{count(s.no_church_size)} of {count(s.postings)} postings don’t state church size.</p>
                  </Card>}
                </div>

                <Card as="section" className="span-7 fill" aria-labelledby="h-dist">
                  <CardHeader>
                    <CardTitle id="h-dist">How pay is spread</CardTitle>
                    <CardDescription>{count(s.paid)} postings with pay</CardDescription>
                  </CardHeader>
                  {s.paid > 0
                    ? <PayDistribution histogram={summary.histogram} bin={summary.histogram_bin} cap={summary.histogram_cap} median={s.median} />
                    : <p className="empty-line">None of the matching postings list pay.</p>}
                </Card>

                <Card as="section" className="span-5" aria-labelledby="h-denom">
                  <CardHeader>
                    <CardTitle id="h-denom">By denomination</CardTitle>
                    <CardDescription>{count(summary.by_denomination.length)} stated</CardDescription>
                  </CardHeader>
                  <BreakdownList rows={summary.by_denomination} nameHeader="Denomination" limit={7} selected={filters.denomination} onSelect={(v) => setFilter("denomination", v)} />
                  <p className="card-note">{count(s.no_denomination)} of {count(s.postings)} postings don’t state a denomination.</p>
                </Card>
              </>
            )}

            <Card as="section" className="table-card span-12" aria-labelledby="h-postings">
              <CardHeader>
                <CardTitle id="h-postings">Postings</CardTitle>
                <CardDescription>{s ? `${count(s.postings)} matching · newest first` : ""}</CardDescription>
              </CardHeader>
              <JobsTable rows={rows} onReady={setTable} onOpen={setOpenJob} />
            </Card>
          </div>
        )}
      {openJob && (
        <JobDetail
          job={openJob}
          onDelete={canEdit ? () => postJSON(`/api/admin/jobs?${toQuery({ source, id: openJob.post_uuid })}`, undefined, "DELETE")
            .then(() => { setOpenJob(null); load(source, filters); fetchSources().then(setSources).catch(() => {}); }) : null}
          onClose={() => setOpenJob(null)}
          returnFocus={() => document.querySelector(`button.job-title[data-id="${CSS.escape(openJob.post_uuid)}"]`)?.focus()}
        />
      )}
    </>
  );
}
