import React from "react";
import { MIN_PAID, count, money, percent, range } from "../format.js";

function Kpi({ label, value, sub, lead = false, suffix }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value num${lead ? " lead" : ""}`}>
        {value}
        {suffix && <span className="suffix">{suffix}</span>}
      </div>
      <div className="kpi-sub">{sub}</div>
    </div>
  );
}

export default function KpiStrip({ stats, loading }) {
  if (loading) {
    return (
      <div className="card kpis" aria-busy="true">
        {["Median pay", "Middle half earn", "Postings with pay", "Employers"].map((label, i) => (
          <div className="kpi" key={label}>
            <div className="kpi-label">{label}</div>
            <div className={`kpi-value${i === 0 ? " lead" : ""}`}><span className="skeleton" style={{ width: i < 2 ? 150 : 80 }}>0</span></div>
            <div className="kpi-sub"><span className="skeleton" style={{ width: 120 }}>0</span></div>
          </div>
        ))}
      </div>
    );
  }

  const benchmarked = stats.paid >= MIN_PAID;
  return (
    <div className="card kpis">
      <Kpi lead label="Median pay" value={benchmarked ? money(stats.median) : "—"} suffix={benchmarked ? "/yr" : null}
        sub={benchmarked ? "Hourly pay counted at 2,080 hrs a year" : `Needs ${MIN_PAID}+ postings with pay`} />
      <Kpi label="Middle half earn" value={benchmarked ? range(stats.p25, stats.p75) : "—"}
        sub="25th to 75th percentile" />
      <Kpi label="Postings with pay" value={count(stats.paid)} suffix={`of ${count(stats.postings)}`}
        sub={stats.postings ? `${percent(stats.paid, stats.postings)} list a salary` : "No matching postings"} />
      <Kpi label="Employers" value={count(stats.employers)}
        sub={`${count(stats.denominations)} denominations stated`} />
    </div>
  );
}
