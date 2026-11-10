import React, { useEffect, useState } from "react";
import { count, longDate } from "./format.js";

const PURPOSES = { extract: "Job extraction", church_lookup: "Church size lookup" };

// AI calls cost fractions of a cent, so show cents precisely and tiny amounts to 4 decimals.
const usd = (n) => {
  const v = Number(n) || 0;
  return v > 0 && v < 1 ? `$${v.toFixed(4)}` : `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};
const when = (t) => new Date(t).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function AiCosts() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/admin/costs")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Couldn’t load costs (${r.status})`))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!data) return <section className="card" aria-busy="true"><span className="skeleton" style={{ width: 240 }}>Loading</span></section>;

  const t = data.totals;
  return (
    <>
      <section className="card kpis cost-kpis">
        <div className="kpi">
          <div className="kpi-label">Total AI spend</div>
          <div className="kpi-value lead num">{usd(t.total)}</div>
          <div className="kpi-sub">{t.since ? `Since ${longDate(t.since)}` : "No AI calls yet"}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">This month</div>
          <div className="kpi-value num">{usd(t.this_month)}</div>
          <div className="kpi-sub">Today {usd(t.today)}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">AI calls</div>
          <div className="kpi-value num">{count(t.calls)}</div>
          <div className="kpi-sub">{count(t.web_searches)} web search{Number(t.web_searches) === 1 ? "" : "es"}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Tokens</div>
          <div className="kpi-value num">{count(Number(t.input_tokens) + Number(t.output_tokens))}</div>
          <div className="kpi-sub">{count(t.input_tokens)} in · {count(t.output_tokens)} out</div>
        </div>
      </section>

      <div className="cost-grid">
        <section className="card">
          <div className="card-head"><h2>By purpose</h2></div>
          {data.by_purpose.length === 0 ? <p className="empty-line">No AI calls yet.</p> : (
            <table className="plain-table">
              <thead><tr><th>Purpose</th><th className="r">Calls</th><th className="r">Avg per call</th><th className="r">Total</th></tr></thead>
              <tbody>
                {data.by_purpose.map((p) => (
                  <tr key={p.purpose}>
                    <td>{PURPOSES[p.purpose] || p.purpose}</td>
                    <td className="r num">{count(p.calls)}</td>
                    <td className="r num">{usd(p.avg_cost)}</td>
                    <td className="r num">{usd(p.cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card">
          <div className="card-head"><h2>By day</h2><span className="meta">Last 30 days</span></div>
          {data.by_day.length === 0 ? <p className="empty-line">No AI calls in the last 30 days.</p> : (
            <table className="plain-table">
              <thead><tr><th>Day</th><th className="r">Calls</th><th className="r">Spend</th></tr></thead>
              <tbody>
                {data.by_day.map((d) => (
                  <tr key={d.day}><td>{longDate(d.day)}</td><td className="r num">{count(d.calls)}</td><td className="r num">{usd(d.cost)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-head"><h2>Recent AI calls</h2><span className="meta">Latest {count(data.recent.length)}</span></div>
        {data.recent.length === 0 ? <p className="empty-line">No AI calls yet.</p> : (
          <div className="table-scroll">
            <table className="plain-table">
              <thead>
                <tr><th>When</th><th>Purpose</th><th>Job URL</th><th>Admin</th><th className="r">Tokens in / out</th><th className="r">Searches</th><th className="r">Cost</th></tr>
              </thead>
              <tbody>
                {data.recent.map((r, i) => (
                  <tr key={i}>
                    <td className="nowrap">{when(r.created_at)}</td>
                    <td className="nowrap">{PURPOSES[r.purpose] || r.purpose}</td>
                    <td className="url-cell"><a href={r.url} target="_blank" rel="noopener noreferrer" title={r.url}>{r.url}</a></td>
                    <td className="muted">{r.admin_email}</td>
                    <td className="r num nowrap">{count(r.input_tokens)} / {count(r.output_tokens)}</td>
                    <td className="r num">{r.web_searches}</td>
                    <td className="r num">{r.cost_usd == null ? "—" : usd(r.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="card-note">
          Estimated from the token counts OpenAI returns for each call and list prices
          ($0.75 / $4.50 per million input / output tokens for gpt-5.4-mini, 1¢ per web search).
          Your OpenAI billing page is the exact figure.{Number(t.unpriced) > 0 && ` ${count(t.unpriced)} calls used a model without a known price and aren’t counted.`}
        </p>
      </section>
    </>
  );
}
