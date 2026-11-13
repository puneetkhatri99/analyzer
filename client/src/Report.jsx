import React, { useEffect, useRef, useState } from "react";
import { fetchReport, fetchReportOptions, reportQuery } from "./api.js";
import { BOOK_URL, CallBand, Footer, HOW_URL, Header, longDay, savedLead } from "./Brand.jsx";
import { money } from "./format.js";
import { useReveal } from "./motion.js";

const LISTS = ["role", "state", "size", "denomination"];
const SHOWN_DENOMINATIONS = 3;

function filtersFromUrl() {
  const p = new URLSearchParams(window.location.search);
  const f = Object.fromEntries(LISTS.map((k) => [k, p.getAll(k)]));
  f.type = p.get("type") === "part-time" ? "part-time" : "full-time";
  return f;
}

const pay = (v, unit) => (v == null ? "—" : unit === "hour" ? `$${v.toFixed(2)}` : money(v));
const per = (unit) => (unit === "hour" ? "/ hour" : "/ year");

function offerVerdict(amount, p, unit) {
  const a = pay(amount, unit);
  if (amount < p.low) return ["Below market.", `${a} is below the lower quarter of current openings, so expect fewer strong candidates.`];
  if (amount < p.typical) return ["Within range.", `${a} sits between the lower quarter and typical pay of current openings.`];
  if (amount <= p.high) return ["Competitive.", `${a} sits above typical pay and below the upper quarter of current openings.`];
  return ["Above market.", `${a} is above the upper quarter of current openings.`];
}

// Where a value sits on the range bar, as a % of its width. The bar runs a little past both quarters.
function scale(p) {
  const spread = Math.max(p.high - p.low, p.typical * 0.1);
  const lo = p.low - spread * 0.35, hi = p.high + spread * 0.35;
  return (v) => `${Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100))}%`;
}

function RangeBar({ p, marker }) {
  const at = scale(p);
  return (
    <div className="mh-range">
      <span className="mh-range-typical-label" style={{ left: at(p.typical) }}>Typical</span>
      <div className="mh-range-track">
        <div className="mh-range-band" style={{ left: at(p.low), width: `calc(${at(p.high)} - ${at(p.low)})` }} />
        <div className="mh-range-tick" style={{ left: at(p.typical) }} />
        {marker != null && <div className="mh-range-marker" style={{ left: at(marker) }} title="Your offer" />}
      </div>
      <span className="mh-range-q" style={{ left: at(p.low) }}>Lower quarter</span>
      <span className="mh-range-q" style={{ left: at(p.high) }}>Upper quarter</span>
    </div>
  );
}

function Bars({ rows, selected = [], unit, placeholder = "[$XX,XXX]" }) {
  const max = Math.max(...rows.map((r) => r.typical || 0), 1);
  return (
    <div className="mh-bars">
      {rows.map((r) => {
        const on = selected.includes(r.name);
        return (
          <div key={r.name} className={`mh-bar-row${on ? " is-on" : ""}`}>
            <span className="mh-bar-name">{r.name}</span>
            <span className="mh-bar-track"><span className={`mh-bar${r.typical == null ? " is-empty" : ""}`} style={{ width: r.typical == null ? "40%" : `${(r.typical / max) * 100}%` }} /></span>
            <span className="mh-bar-value">{r.typical == null ? placeholder : pay(r.typical, unit)}</span>
          </div>
        );
      })}
    </div>
  );
}

function ChipList({ label, values, options, onChange }) {
  const left = options.filter((o) => !values.includes(o));
  return (
    <div className="mh-filter">
      <h3>{label}</h3>
      <div className="mh-chips">
        {values.map((v) => (
          <span key={v} className="mh-chip">{v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}>×</button>
          </span>
        ))}
        <label className="mh-chip-add">
          <span aria-hidden="true">+ Add {label.toLowerCase()}</span>
          <select aria-label={`Add ${label.toLowerCase()}`} value="" onChange={(e) => e.target.value && onChange([...values, e.target.value])}>
            <option value="">Add {label.toLowerCase()}</option>
            {left.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
      </div>
    </div>
  );
}

function Checks({ label, options, values, onChange, allLabel }) {
  const toggle = (o) => onChange(values.includes(o) ? values.filter((x) => x !== o) : [...values, o]);
  return (
    <fieldset className="mh-filter">
      <legend>{label}</legend>
      {allLabel && <label className="mh-check"><input type="checkbox" checked={!values.length} onChange={() => onChange([])} />{allLabel}</label>}
      {options.map((o) => <label key={o} className="mh-check"><input type="checkbox" checked={values.includes(o)} onChange={() => toggle(o)} />{o}</label>)}
    </fieldset>
  );
}

// On wide screens the filters sit open beside the report; on narrow ones they fold away above it, so the answer
// is on the first screen instead of below a long panel.
const WIDE = "(min-width: 960px)";
function useWide() {
  const [wide, setWide] = useState(() => window.matchMedia(WIDE).matches);
  useEffect(() => {
    const m = window.matchMedia(WIDE);
    const on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}

function activeSummary(f, opts) {
  const parts = [...f.role, ...f.state, ...f.size, ...f.denomination];
  const type = opts.job_types.find((t) => t.key === f.type)?.label;
  return [...parts, type].filter(Boolean).join(" · ");
}

function Refine({ f, opts, setF }) {
  const [allDenoms, setAllDenoms] = useState(false);
  const wide = useWide();
  const [open, setOpen] = useState(false);
  const set = (key) => (value) => setF({ ...f, [key]: value });
  const denoms = opts.denominations;
  const shown = allDenoms ? denoms : [...new Set([...denoms.slice(0, SHOWN_DENOMINATIONS), ...f.denomination])];
  const reset = () => setF({ ...Object.fromEntries(LISTS.map((k) => [k, []])), role: f.role.slice(0, 1), type: "full-time" });
  return (
    <details className="mh-refine" open={wide || open} onToggle={(e) => !wide && setOpen(e.currentTarget.open)}>
      <summary className="mh-refine-head" onClick={(e) => wide && e.preventDefault()} tabIndex={wide ? -1 : 0}>
        <h2>Refine your report</h2>
        {!wide && <span className="mh-refine-toggle" aria-hidden="true">{open ? "Close" : "Change"}</span>}
        {!wide && <span className="mh-refine-summary">{activeSummary(f, opts)}</span>}
      </summary>
      <div className="mh-refine-body">
        <button type="button" className="mh-link mh-reset" onClick={reset}>Reset filters</button>
      <ChipList label="Role" values={f.role} options={opts.roles} onChange={set("role")} />
      <ChipList label="State" values={f.state} options={opts.states} onChange={set("state")} />
      <Checks label="Weekly attendance" options={opts.sizes} values={f.size} onChange={set("size")} />
      <Checks label="Denomination" options={shown} values={f.denomination} onChange={set("denomination")} allLabel="All denominations" />
      {denoms.length > SHOWN_DENOMINATIONS && (
        <button type="button" className="mh-link mh-show-all" onClick={() => setAllDenoms(!allDenoms)}>{allDenoms ? "Show fewer" : "Show all"}</button>
      )}
      <fieldset className="mh-filter">
        <legend>Job type</legend>
        {opts.job_types.map((t) => (
          <label key={t.key} className="mh-check"><input type="radio" name="type" checked={f.type === t.key} onChange={() => setF({ ...f, type: t.key })} />{t.label}</label>
        ))}
      </fieldset>
      </div>
    </details>
  );
}

function OfferCheck({ r }) {
  const [text, setText] = useState("");
  const [amount, setAmount] = useState(null);
  const [problem, setProblem] = useState(null);
  const p = r.pay;
  const check = (e) => {
    e.preventDefault();
    const n = parseFloat(text.replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(n) || n <= 0) {
      setAmount(null);
      return setProblem(`Enter the ${r.unit === "hour" ? "hourly rate" : "yearly salary"} as a number, for example ${r.unit === "hour" ? "18.50" : "52,000"}.`);
    }
    setProblem(null);
    setAmount(n);
    setText(pay(n, r.unit));
  };
  const verdict = amount != null && offerVerdict(amount, p, r.unit);
  return (
    <section className="mh-card" data-reveal>
      <h2>Check my offer</h2>
      <p className="mh-muted">Enter the {r.unit === "hour" ? "hourly rate" : "salary"} you're planning to offer and see where it lands.</p>
      <form className="mh-offer" onSubmit={check}>
        <label className="mh-field">
          <span>Planned {r.unit === "hour" ? "hourly rate" : "salary"}</span>
          <input inputMode="decimal" placeholder={r.unit === "hour" ? "$18.00" : "$52,000"} value={text} onChange={(e) => setText(e.target.value)}
            aria-invalid={problem ? true : undefined} aria-describedby={problem ? "offer-problem" : undefined} />
        </label>
        <button type="submit" className="mh-btn mh-btn-teal">Check</button>
      </form>
      {problem && <p id="offer-problem" className="mh-error" role="alert">{problem}</p>}
      {verdict && (
        <>
          <RangeBar p={p} marker={amount} />
          <p className="mh-offer-verdict" role="status"><strong>{verdict[0]}</strong> {verdict[1]}</p>
        </>
      )}
    </section>
  );
}

function Stats({ r, roleText, compact }) {
  const v = r.vs_national;
  return (
    <div className="mh-stats" data-reveal>
      <div className="mh-card mh-stat">
        <h3>{v ? `${v.area} vs. national, all ${compact ? "roles" : "ministry roles"}` : "Compared with national"}</h3>
        {v ? (
          <>
            <strong>{v.percent === 0 ? "On par" : `${Math.abs(v.percent)}% ${v.percent < 0 ? "lower" : "higher"}`}</strong>
            <p>{pay(v.area_typical, r.unit)} in {v.area}, {pay(v.national_typical, r.unit)} nationwide</p>
          </>
        ) : <p>Pick a state to compare it with national pay.</p>}
      </div>
      <div className="mh-card mh-stat">
        <h3>Typical time open</h3>
        <strong>{r.days_open != null ? `${r.days_open} days` : "[XX] days"}</strong>
        <p>How long {roleText} roles stay posted</p>
      </div>
      <div className="mh-card mh-stat">
        <h3>Share of openings</h3>
        <strong>{r.share_percent != null ? `${r.share_percent < 1 ? "<1" : r.share_percent}%` : "—"}</strong>
        <p>{r.share_percent != null ? `of current ministry openings are ${roleText} roles` : "Pick a role to see its share."}</p>
      </div>
    </div>
  );
}

function PayCard({ r, typeLabel }) {
  const p = r.pay;
  if (!p) return <section className="mh-pay"><h2 className="mh-pay-label">Typical pay, {typeLabel}</h2><p className="mh-pay-empty">{r.note}</p></section>;
  return (
    <section className="mh-pay" data-reveal>
      <div className="mh-pay-top">
        <div>
          <h2 className="mh-pay-label">Typical pay, {typeLabel}</h2>
          <p className="mh-pay-big">{pay(p.typical, r.unit)}<span>{per(r.unit)}</span></p>
        </div>
        <div className="mh-pay-range">
          <span>Most churches offer</span>
          <strong>{pay(p.low, r.unit)} – {pay(p.high, r.unit)}</strong>
        </div>
      </div>
      <RangeBar p={p} />
      <span className="mh-confidence"><i aria-hidden="true" />Confidence: {p.confidence}</span>
      <p className="mh-pay-foot">Drawn from {r.openings_label} active ministry job openings. Data as of {longDay(r.as_of)}.</p>
    </section>
  );
}

const insightText = (roleText) =>
  `[Two or three sentences from the MinistryHub team on ${roleText} searches right now: what candidates expect, what is slowing searches down, and one piece of practical advice.]`;

// The branded export (brief P8): shown only when printing, so "Download report" saves it as a PDF.
function PrintReport({ r, lead, roleText, typeLabel }) {
  return (
    <div className="mh-print" aria-hidden="true">
      <div className="mh-print-head">
        <img className="mh-logo" src="/ministryhub-logo.png" alt="" />
        <div><p className="mh-eyebrow">Market Analysis Report</p><p>{longDay(new Date().toISOString())}</p></div>{/* taste-skill-ignore: label in the client's approved design */}
      </div>
      <h1>{r.title.role} pay in <span className="mh-underline">{r.title.area}</span></h1>
      {lead && <p className="mh-print-for">Prepared for {lead.name}, {lead.organization}</p>}
      <PayCard r={r} typeLabel={typeLabel} />
      <Stats r={r} roleText={roleText} compact />
      <div className="mh-print-cols">
        <section className="mh-card"><h2>Compared with other roles</h2><Bars rows={r.by_role} selected={r.filters.role} unit={r.unit} /></section>
        <section className="mh-card"><h2>By weekly attendance</h2><Bars rows={r.by_size} selected={r.filters.size} unit={r.unit} /></section>
      </div>
      <section className="mh-insight"><div><h2>What our search team is seeing</h2><p>{r.insight || insightText(roleText)}</p></div></section>
      <p className="mh-print-note">
        {r.note ? `${r.note} ` : ""}Drawn from {r.openings_label} active ministry job openings; {typeLabel} roles; data as of {longDay(r.as_of)}.
        A guide for planning, not a guarantee of what any candidate will accept.
      </p>
      <div className="mh-print-foot">
        <img className="mh-logo" src="/ministryhub-logo-white.png" alt="" />
        <div><p>Hiring soon? Let's talk through your search.</p><strong>{BOOK_URL.replace("https://", "")}</strong></div>
      </div>
    </div>
  );
}

export default function Report() {
  const [lead] = useState(savedLead);
  const [f, setF] = useState(filtersFromUrl);
  const [opts, setOpts] = useState(null);
  const [r, setR] = useState(null);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(true);
  const requestId = useRef(0);

  // shortcut: the sign-up gate is in the browser only; the report API returns summary figures, nothing private
  useEffect(() => { if (!lead) window.location.replace("/"); }, [lead]);
  useEffect(() => { fetchReportOptions().then(setOpts).catch(() => {}); }, []);
  useEffect(() => {
    const q = reportQuery(f);
    window.history.replaceState(null, "", `/report${q ? `?${q}` : ""}`);
    const id = ++requestId.current;
    setUpdating(true);
    const t = setTimeout(() => fetchReport(f)
      .then((x) => { if (id === requestId.current) { setR(x); setError(null); } })
      .catch((e) => id === requestId.current && setError(e.message))
      .finally(() => id === requestId.current && setUpdating(false)), 150);
    return () => clearTimeout(t);
  }, [f]);

  useReveal(r);

  if (!lead) return null;
  const roleText = r ? r.title.role : "these";
  const typeLabel = f.type === "part-time" ? "part-time" : "full-time";

  return (
    <div className="mh">
      <div className="mh-screen">
        <Header />
        <main className="mh-wrap mh-report">
          <div className="mh-report-head" data-reveal>
            <div>
              <p className="mh-eyebrow">Market Analysis Report</p>{/* taste-skill-ignore: label in the client's approved design */}
              <h1>{r ? <>{r.title.role} pay in <span className="mh-underline">{r.title.area}</span></> : "Loading your report…"}</h1>
            </div>
            <div className="mh-report-actions">
              <a className="mh-btn mh-btn-outline" href="/">New search</a>
              <button type="button" className="mh-btn mh-btn-yellow" onClick={() => window.print()} disabled={!r}>
                <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8m0 0l-3-3m3 3l3-3M3 13h10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                Download report
              </button>
            </div>
          </div>

          <div className="mh-report-grid">
            {opts ? <Refine f={f} opts={opts} setF={setF} /> : <aside className="mh-refine" />}

            <div className={`mh-report-main${updating && r ? " is-updating" : ""}`} aria-live="polite" aria-busy={updating}>
              {error && <p className="mh-note" role="alert">We couldn't load the report ({error}). Please try again in a minute.</p>}
              {r && (
                <>
                  {r.note && r.pay && (
                    <p className="mh-note">
                      <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.5" /><path d="M10 9v5M10 6.2v.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
                      <span><strong>{r.note.split(". ")[0]}.</strong> {r.note.split(". ").slice(1).join(". ")}</span>
                    </p>
                  )}
                  <PayCard r={r} typeLabel={typeLabel} />
                  <Stats r={r} roleText={roleText} />
                  {r.pay && <OfferCheck key={`${r.unit}-${r.pay.typical}`} r={r} />}
                  <section className="mh-card" data-reveal>
                    <h2>Compared with other roles{r.scope !== "national" ? ` in ${r.area_name}` : ""}</h2>
                    {r.by_role.length ? <Bars rows={r.by_role} selected={r.filters.role} unit={r.unit} /> : <p className="mh-muted">Not enough listed pay to compare roles yet.</p>}
                  </section>
                  <section className="mh-card" data-reveal>
                    <h2>By weekly attendance</h2>
                    <Bars rows={r.by_size} selected={r.filters.size} unit={r.unit} />
                    {r.filters.size.length > 0 && <p className="mh-small">Your selected sizes are highlighted.</p>}
                  </section>
                  <div className="mh-two" data-reveal>
                    <section className="mh-card">
                      <h2>Pay by state</h2>
                      {r.by_state.length ? <Bars rows={r.by_state} selected={r.filters.state} unit={r.unit} /> : <p className="mh-muted">Not enough listed pay by state yet.</p>}
                    </section>
                    <section className="mh-card">
                      <h2>By denomination</h2>
                      {r.by_denomination.length ? <Bars rows={r.by_denomination} selected={r.filters.denomination} unit={r.unit} /> : <p className="mh-muted">Not enough listed pay by denomination yet.</p>}
                    </section>
                  </div>
                  <section className="mh-insight" data-reveal>
                    <span className="mh-bulb" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z" /></svg></span>
                    <div><h2>What our search team is seeing</h2><p>{r.insight || insightText(roleText)}</p></div>
                  </section>
                  <CallBand
                    title={`Hiring for ${r.title.role}?`}
                    secondary={<a className="mh-band-link" href={HOW_URL}>See how our searches work</a>}
                  >
                    Let's talk through your search in {r.title.area}. A responsive partner from first call to first day:
                    we reply promptly, update you every two weeks, and never go quiet.
                  </CallBand>
                </>
              )}
            </div>
          </div>
        </main>
        <Footer />
      </div>
      {r && <PrintReport r={r} lead={lead} roleText={roleText} typeLabel={typeLabel} />}
    </div>
  );
}
