import React, { useState } from "react";
import { count, money } from "../format.js";

const CHURCH_SIZES = [
  [250, "250+ attendance"],
  [1000, "1,000+ attendance"],
  [5000, "5,000+ attendance"],
];
const MIN_PAY = [30000, 40000, 50000, 60000, 80000, 100000];
const MORE_KEYS = ["status", "country", "remote", "min_salary", "has_pay"];
const STATUS = { open: "Still open", expired: "Expired", unverified: "Not verified" };

function Select({ id, label, value, onChange, children }) {
  return (
    <select
      id={id}
      aria-label={label}
      className={`control${value ? " is-set" : ""}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {children}
    </select>
  );
}

const options = (pairs) => pairs.map(([name, n]) => <option key={name} value={name}>{name} ({count(n)})</option>);

function describe(key, value) {
  switch (key) {
    case "search": return ["Search", `“${value}”`];
    case "role": return ["Role", value];
    case "region": return ["State", value];
    case "denomination": return ["Denomination", value];
    case "min_church_size": return ["Church size", `${count(value)}+`];
    case "hours": return ["Type", value];
    case "status": return ["Status", STATUS[value]];
    case "country": return ["Country", value];
    case "remote": return [value === "true" ? "Remote only" : "On-site only", null];
    case "min_salary": return ["Pay", `${money(value)}+`];
    case "has_pay": return ["Listed pay only", null];
    default: return [key, value];
  }
}

function XIcon() {
  return <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>;
}

export default function FilterBar({ filters, setFilter, clearFilter, resetFilters, options: opts, showChurchSize = true }) {
  const moreActive = MORE_KEYS.filter((k) => filters[k]).length;
  const [moreOpen, setMoreOpen] = useState(moreActive > 0);
  const [panelOpen, setPanelOpen] = useState(false);
  const o = opts || { roles: [], denominations: [], regions: [], countries: [], hours: [] };
  const active = Object.entries(filters).filter(([, v]) => v !== "" && v !== 0 && v !== false);

  return (
    <section className="filters" aria-label="Filters">
      <button type="button" className="btn filters-toggle" aria-expanded={panelOpen} onClick={() => setPanelOpen((v) => !v)}>
        {panelOpen ? "Hide filters" : `Filters${active.length ? ` (${active.length})` : ""}`}
      </button>

      <div className={`filter-panel${panelOpen ? " is-open" : ""}`}>
        <div className="filter-row">
          <label className="search">
            <span className="sr-only">Search job title or employer</span>
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" /><path d="M11 11l3.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            <input
              id="f-search"
              type="search"
              className="control"
              placeholder="Search title or employer"
              value={filters.search}
              onChange={(e) => setFilter("search", e.target.value)}
            />
          </label>
          <Select id="f-role" label="Role" value={filters.role} onChange={(v) => setFilter("role", v)}>
            <option value="">All roles</option>{options(o.roles)}
          </Select>
          <Select id="f-region" label="State" value={filters.region} onChange={(v) => setFilter("region", v)}>
            <option value="">All states</option>{options(o.regions)}
          </Select>
          <Select id="f-denom" label="Denomination" value={filters.denomination} onChange={(v) => setFilter("denomination", v)}>
            <option value="">All denominations</option>{options(o.denominations)}
          </Select>
          {showChurchSize && (
            <Select id="f-size" label="Church size" value={filters.min_church_size || ""} onChange={(v) => setFilter("min_church_size", Number(v) || 0)}>
              <option value="">Any church size</option>
              {CHURCH_SIZES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
            </Select>
          )}
          <Select id="f-hours" label="Employment type" value={filters.hours} onChange={(v) => setFilter("hours", v)}>
            <option value="">Any job type</option>{options(o.hours)}
          </Select>
          <button type="button" className="btn" aria-expanded={moreOpen} aria-controls="more-filters" onClick={() => setMoreOpen((v) => !v)}>
            More filters{moreActive ? ` (${moreActive})` : ""}
            <svg width="10" height="6" viewBox="0 0 10 6" aria-hidden="true" style={{ transform: moreOpen ? "rotate(180deg)" : "none", transition: "transform 150ms" }}><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
          </button>
        </div>

        {moreOpen && (
          <div className="more-row" id="more-filters">
            <Select id="f-status" label="Job status" value={filters.status} onChange={(v) => setFilter("status", v)}>
              <option value="">Open or expired</option>
              {Object.entries(STATUS).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
            </Select>
            <Select id="f-country" label="Country" value={filters.country} onChange={(v) => setFilter("country", v)}>
              <option value="">All countries</option>{options(o.countries)}
            </Select>
            <Select id="f-remote" label="Remote" value={filters.remote} onChange={(v) => setFilter("remote", v)}>
              <option value="">Remote or on-site</option>
              <option value="true">Remote only</option>
              <option value="false">On-site only</option>
            </Select>
            <Select id="f-pay" label="Minimum pay" value={filters.min_salary || ""} onChange={(v) => setFilter("min_salary", Number(v) || 0)}>
              <option value="">Any pay</option>
              {MIN_PAY.map((v) => <option key={v} value={v}>{money(v)}+ a year</option>)}
            </Select>
            <label className="check">
              <input id="f-has-pay" type="checkbox" checked={filters.has_pay} onChange={(e) => setFilter("has_pay", e.target.checked)} />
              Listed pay only
            </label>
          </div>
        )}
      </div>

      {active.length > 0 && (
        <div className="chips" aria-label="Active filters">
          {active.map(([key, value]) => {
            const [name, detail] = describe(key, value);
            return (
              <button type="button" key={key} className="chip" onClick={() => clearFilter(key)} aria-label={`Remove filter ${name}${detail ? ` ${detail}` : ""}`}>
                <span>{name}{detail && <>: <b>{detail}</b></>}</span>
                <XIcon />
              </button>
            );
          })}
          <button type="button" className="link-btn" style={{ marginLeft: 6, fontSize: 13 }} onClick={resetFilters}>Clear all</button>
        </div>
      )}
    </section>
  );
}
