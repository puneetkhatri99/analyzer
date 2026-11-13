import React, { useEffect, useState } from "react";
import { fetchCosts } from "@/api/admin.js";
import SimpleTable from "@/components/SimpleTable.jsx";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count } from "@/lib/format.js";
import { BY_DAY, BY_PURPOSE, RECENT } from "./costColumns.jsx";
import CostKpis from "./CostKpis.jsx";

function TableCard({ title, meta, children }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle>{meta && <CardDescription>{meta}</CardDescription>}</CardHeader>
      {children}
    </Card>
  );
}

// Admin only: what the AI calls behind "Add a job" and church-size lookups have cost.
export default function CostsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { fetchCosts().then(setData).catch((e) => setError(`Couldn’t load costs (${e.message})`)); }, []);

  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!data) return <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

  const t = data.totals;
  return (
    <>
      <CostKpis totals={t} />
      <div className="cost-grid">
        <TableCard title="By purpose">
          <SimpleTable columns={BY_PURPOSE} rows={data.by_purpose} rowKey={(p) => p.purpose} empty="No AI calls yet." />
        </TableCard>
        <TableCard title="By day" meta="Last 30 days">
          <SimpleTable columns={BY_DAY} rows={data.by_day} rowKey={(d) => d.day} empty="No AI calls in the last 30 days." />
        </TableCard>
      </div>
      <TableCard title="Recent AI calls" meta={`Latest ${count(data.recent.length)}`}>
        <SimpleTable columns={RECENT} rows={data.recent} empty="No AI calls yet." />
        <p className="card-note">
          Estimated from the token counts OpenAI returns for each call and list prices
          ($0.75 / $4.50 per million input / output tokens for gpt-5.4-mini, 1¢ per web search).
          Your OpenAI billing page is the exact figure.
          {Number(t.unpriced) > 0 && ` ${count(t.unpriced)} calls used a model without a known price and aren’t counted.`}
        </p>
      </TableCard>
    </>
  );
}
