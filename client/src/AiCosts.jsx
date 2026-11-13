import React, { useEffect, useState } from "react";
import { count, longDate } from "./format.js";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
  if (!data) return <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

  const t = data.totals;
  return (
    <>
      <Card className="kpis cost-kpis">
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
      </Card>

      <div className="cost-grid">
        <Card>
          <CardHeader><CardTitle>By purpose</CardTitle></CardHeader>
          {data.by_purpose.length === 0 ? <p className="empty-line">No AI calls yet.</p> : (
            <Table>
              <TableHeader><TableRow><TableHead>Purpose</TableHead><TableHead className="text-right">Calls</TableHead><TableHead className="text-right">Avg per call</TableHead><TableHead className="text-right">Total</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.by_purpose.map((p) => (
                  <TableRow key={p.purpose}>
                    <TableCell>{PURPOSES[p.purpose] || p.purpose}</TableCell>
                    <TableCell className="num text-right">{count(p.calls)}</TableCell>
                    <TableCell className="num text-right">{usd(p.avg_cost)}</TableCell>
                    <TableCell className="num text-right">{usd(p.cost)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>By day</CardTitle><CardDescription>Last 30 days</CardDescription></CardHeader>
          {data.by_day.length === 0 ? <p className="empty-line">No AI calls in the last 30 days.</p> : (
            <Table>
              <TableHeader><TableRow><TableHead>Day</TableHead><TableHead className="text-right">Calls</TableHead><TableHead className="text-right">Spend</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.by_day.map((d) => (
                  <TableRow key={d.day}><TableCell>{longDate(d.day)}</TableCell><TableCell className="num text-right">{count(d.calls)}</TableCell><TableCell className="num text-right">{usd(d.cost)}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Recent AI calls</CardTitle><CardDescription>Latest {count(data.recent.length)}</CardDescription></CardHeader>
        {data.recent.length === 0 ? <p className="empty-line">No AI calls yet.</p> : (
                      <Table>
              <TableHeader>
                <TableRow><TableHead>When</TableHead><TableHead>Purpose</TableHead><TableHead>Job URL</TableHead><TableHead>Admin</TableHead><TableHead className="text-right">Tokens in / out</TableHead><TableHead className="text-right">Searches</TableHead><TableHead className="text-right">Cost</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {data.recent.map((r, i) => (
                  <TableRow key={i}>
                    <TableCell>{when(r.created_at)}</TableCell>
                    <TableCell>{PURPOSES[r.purpose] || r.purpose}</TableCell>
                    <TableCell className="url-cell"><a href={r.url} target="_blank" rel="noopener noreferrer" title={r.url}>{r.url}</a></TableCell>
                    <TableCell className="muted">{r.admin_email}</TableCell>
                    <TableCell className="num text-right">{count(r.input_tokens)} / {count(r.output_tokens)}</TableCell>
                    <TableCell className="num text-right">{r.web_searches}</TableCell>
                    <TableCell className="num text-right">{r.cost_usd == null ? "—" : usd(r.cost_usd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
        )}
        <p className="card-note">
          Estimated from the token counts OpenAI returns for each call and list prices
          ($0.75 / $4.50 per million input / output tokens for gpt-5.4-mini, 1¢ per web search).
          Your OpenAI billing page is the exact figure.{Number(t.unpriced) > 0 && ` ${count(t.unpriced)} calls used a model without a known price and aren’t counted.`}
        </p>
      </Card>
    </>
  );
}
