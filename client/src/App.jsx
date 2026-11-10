import React, { useCallback, useEffect, useRef, useState } from "react";
import FilterBar from "./components/FilterBar.jsx";
import KpiStrip from "./components/KpiStrip.jsx";
import PayLadder from "./components/PayLadder.jsx";
import BreakdownList from "./components/BreakdownList.jsx";
import PayDistribution from "./components/PayDistribution.jsx";
import JobsTable from "./components/JobsTable.jsx";
import SourceTabs from "./components/SourceTabs.jsx";
import JobDetail from "./components/JobDetail.jsx";
import { fetchFilterOptions, fetchJobs, fetchSources, fetchSummary, toQuery } from "./api.js";
import { MIN_PAID, count, longDate, money } from "./format.js";

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

export function Mark() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="#141414" />
      <rect x="6" y="7" width="12" height="2" rx="1" fill="#fff" />
      <rect x="6" y="11" width="8" height="2" rx="1" fill="#fff" />
      <rect x="6" y="15" width="10" height="2" rx="1" fill="#fff" />
    </svg>
  );
}

function LoadingCard({ className, title, rows = 6 }) {
  return (
    <section className={`card ${className}`} aria-busy="true">
      <div className="card-head"><h2>{title}</h2></div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} style={{ height: 32, display: "flex", alignItems: "center" }}>
          <span className="skeleton" style={{ width: `${90 - i * 8}%`, height: 10 }} />
        </div>
      ))}
    </section>
  );
}

export default function App() {
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
  const exportCsv = () => table?.download("csv", `ministry-jobs-${source}-${new Date().toISOString().slice(0, 10)}.csv`);

  const s = summary?.stats;
  const current = sources?.find((x) => x.key === source);
  const isChurch = source !== "nonprofits";

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand"><Mark />Ministry Jobs Analyser</div>
          <div className="freshness">{current?.label || "…"} · {source === "json" ? "data as of" : "pages last read"} {s?.as_of ? longDate(s.as_of) : "…"}</div>
        </div>
      </header>

      <main className="canvas">
        <SourceTabs sources={sources} value={source} onChange={changeSource} />

        <div className="title-row">
          <div>
            <h1>Salary benchmarks</h1>
            <p className="finding" aria-live="polite">
              {s ? finding(filters, s) : <span className="skeleton" style={{ width: 520 }}>Loading</span>}
            </p>
          </div>
          <button type="button" className="btn btn-primary" onClick={exportCsv} disabled={!table || !s?.postings}>
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8m0 0l-3-3m3 3l3-3M3 13h10" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Export {s ? count(s.postings) : ""} postings
          </button>
        </div>

        <FilterBar filters={filters} setFilter={setFilter} clearFilter={clearFilter} resetFilters={resetFilters} options={options} showChurchSize={isChurch} />

        {error && (
          <div className="card error-card" role="alert">
            <strong>Couldn’t load the benchmarks.</strong>
            <span className="muted">The server didn’t answer ({error}). It may be waking up; try again in a minute.</span>
            <button type="button" className="btn" onClick={() => load(source, filters)}>Retry</button>
          </div>
        )}

        {!error && (
          <div className={`grid${updating && summary ? " is-updating" : ""}`} aria-busy={updating}>
            <div className="span-12"><KpiStrip stats={s} loading={!s} /></div>

            {!summary ? (
              <>
                <LoadingCard className="span-7" title="Pay by role" rows={12} />
                <LoadingCard className="span-5" title="Pay by state" rows={12} />
              </>
            ) : (
              <>
                <section className="card span-7" aria-labelledby="h-role">
                  <div className="card-head">
                    <h2 id="h-role">Pay by role</h2>
                    <div className="legend" aria-hidden="true">
                      <span><i className="sw-band" />Middle half</span>
                      <span><i className="sw-tick" />Median</span>
                    </div>
                  </div>
                  <PayLadder rows={summary.by_role} nameHeader="Role" selected={filters.role} onSelect={(v) => setFilter("role", v)} />
                  <p className="card-note">Annual pay; hourly roles counted at 2,080 hours. Role is matched from the job title. Roles with fewer than {MIN_PAID} paid postings aren’t benchmarked.</p>
                </section>

                <div className="stack span-5">
                  <section className="card" aria-labelledby="h-state">
                    <div className="card-head">
                      <h2 id="h-state">Pay by state</h2>
                      <span className="meta">Top 10 by postings</span>
                    </div>
                    <PayLadder compact rows={summary.by_state} nameHeader="State" selected={filters.region} onSelect={(v) => setFilter("region", v)} />
                  </section>

                  {isChurch && <section className="card" aria-labelledby="h-size">
                    <div className="card-head">
                      <h2 id="h-size">By church size</h2>
                      <span className="meta">Weekly attendance</span>
                    </div>
                    <BreakdownList rows={summary.by_church_size.filter((r) => r.postings > 0)} nameHeader="Attendance" />
                    <p className="card-note">{count(s.no_church_size)} of {count(s.postings)} postings don’t state church size.</p>
                  </section>}
                </div>

                <section className="card span-7 fill" aria-labelledby="h-dist">
                  <div className="card-head">
                    <h2 id="h-dist">How pay is spread</h2>
                    <span className="meta">{count(s.paid)} postings with pay</span>
                  </div>
                  {s.paid > 0
                    ? <PayDistribution histogram={summary.histogram} bin={summary.histogram_bin} cap={summary.histogram_cap} median={s.median} />
                    : <p className="empty-line">None of the matching postings list pay.</p>}
                </section>

                <section className="card span-5" aria-labelledby="h-denom">
                  <div className="card-head">
                    <h2 id="h-denom">By denomination</h2>
                    <span className="meta">{count(summary.by_denomination.length)} stated</span>
                  </div>
                  <BreakdownList rows={summary.by_denomination} nameHeader="Denomination" limit={7} selected={filters.denomination} onSelect={(v) => setFilter("denomination", v)} />
                  <p className="card-note">{count(s.no_denomination)} of {count(s.postings)} postings don’t state a denomination.</p>
                </section>
              </>
            )}

            <section className="card table-card span-12" aria-labelledby="h-postings">
              <div className="card-head">
                <h2 id="h-postings">Postings</h2>
                <span className="meta">{s ? `${count(s.postings)} matching · newest first` : ""}</span>
              </div>
              <JobsTable rows={rows} onReady={setTable} onOpen={setOpenJob} />
            </section>
          </div>
        )}
      </main>
      {openJob && (
        <JobDetail
          job={openJob}
          onClose={() => {
            // The table may redraw its rows while the dialog is open, so find the row again to return focus to it.
            table?.getRow(openJob.post_uuid)?.getElement?.().querySelector("button.job-title")?.focus();
            setOpenJob(null);
          }}
        />
      )}
    </>
  );
}
