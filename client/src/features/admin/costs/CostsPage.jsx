import React, { useEffect, useState } from "react";
import { fetchCosts } from "@/api/admin.js";
import SimpleTable from "@/components/SimpleTable.jsx";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { count } from "@/lib/format.js";
import PageHead from "../components/PageHead.jsx";
import { BY_DAY, BY_PURPOSE, BY_RUN } from "./costColumns.jsx";
import CallsTable from "./CallsTable.jsx";
import CostKpis from "./CostKpis.jsx";
import { usd } from "./costFormat.js";
import PricingDialog from "./PricingDialog.jsx";
import SpendLimit from "./SpendLimit.jsx";

function TableCard({ title, meta, children }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle>{meta && <CardDescription>{meta}</CardDescription>}</CardHeader>
      {children}
    </Card>
  );
}

// Admin only: what the AI costs, and the monthly limit that stops it (opened from the profile menu).
export default function CostsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [version, setVersion] = useState(0); // bumped after a delete or a new limit: reloads everything
  useEffect(() => { fetchCosts().then(setData).catch((e) => setError(`Couldn’t load costs (${e.message})`)); }, [version]);

  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!data) return <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

  const t = data.totals;
  return (
    <>
      <PageHead title="AI costs" actions={data.pricing && <PricingDialog pricing={data.pricing} />}>
        The AI has cost about {usd(t.this_month)} this month. It reads new jobs, looks up churches and finds pay,
        and you can set the most it may spend each month.
      </PageHead>
      {data.budget && <SpendLimit budget={data.budget} onSaved={() => setVersion((v) => v + 1)} />}
      <CostKpis totals={t} />
      <div className="cost-grid">
        <TableCard title="What the AI was used for">
          <SimpleTable columns={BY_PURPOSE} rows={data.by_purpose} rowKey={(p) => p.purpose} empty="The AI hasn’t been used yet." />
        </TableCard>
        <TableCard title="Day by day" meta="The last 30 days">
          <SimpleTable columns={BY_DAY} rows={data.by_day} rowKey={(d) => d.day} empty="The AI hasn’t been used in the last 30 days." />
        </TableCard>
      </div>
      <TableCard title="Automatic runs" meta="Each time the server ran by itself, and what the AI cost during it">
        <SimpleTable columns={BY_RUN} rows={data.by_run || []} rowKey={(r) => r.run_id} empty="Nothing has run by itself yet." />
      </TableCard>
      <TableCard title="Every AI request" meta="The full list, newest first. You only need this if something looks wrong.">
        <details className="px-6 pb-2">
          <summary className="cursor-pointer text-sm font-medium">Show the full list ({count(t.calls)} requests)</summary>
          <div className="pt-4">
            <CallsTable purposes={data.by_purpose.map((p) => p.purpose)} runs={(data.by_run || []).map((r) => r.run_id)}
              version={version} onChanged={() => setVersion((v) => v + 1)} />
          </div>
        </details>
        <p className="card-note">
          These amounts are estimates, worked out from what OpenAI reports for each request. Your OpenAI billing page is the exact figure.
          {Number(t.unpriced) > 0 && ` ${count(t.unpriced)} requests used a model with no known price and aren’t counted.`}
        </p>
      </TableCard>
    </>
  );
}
