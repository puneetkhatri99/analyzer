import React, { useEffect, useMemo, useState } from "react";
import { Download, Flame } from "lucide-react";
import { fetchLeads } from "@/api/admin.js";
import SimpleTable from "@/components/SimpleTable.jsx";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { downloadCsv, toCsv } from "@/lib/csv.js";
import { count, isoDate, longDate } from "@/lib/format.js";
import Kpi from "../components/Kpi.jsx";
import HotBadge, { BookedBadge } from "./HotBadge.jsx";
import LeadHistory from "./LeadHistory.jsx";
import { when } from "../costs/costFormat.js";

export const placeName = (v) => (v === "nationwide" ? "Nationwide" : v); // the form's "Anywhere in the US"
const searched = (l) => [l.role, placeName(l.location), l.attendance].filter(Boolean).join(" · ") || "—";

// The name opens the lead's full history; organization sits under it so every column fits a laptop screen.
const columns = (open) => [
  {
    header: "Lead",
    cell: (l) => (
      <div className="grid gap-0.5">
        <span>
          <button type="button" className="font-medium text-teal-800 underline underline-offset-2 hover:text-teal-950"
            onClick={() => open(l.email)} aria-label={`${l.name}: open history`}>{l.name}</button>
          {l.hot && <HotBadge />}
          {l.booked && <BookedBadge />}
        </span>
        <span className="text-xs text-muted-foreground">{l.organization}</span>
      </div>
    ),
  },
  { header: "Email", cell: (l) => <a className="no-underline hover:underline" href={`mailto:${l.email}`}>{l.email}</a> },
  { header: "Searched for", className: "muted whitespace-normal min-w-40", cell: searched }, // wraps so "Last active" fits
  { header: "Signed up", cell: (l) => longDate(l.created_at) },
  { header: "Reports", right: true, className: "num", cell: (l) => count(l.reports) },
  { header: "Last active", className: "muted", cell: (l) => (l.last_active ? when(l.last_active) : "—") },
];

const SORTS = {
  newest: ["Newest first", (a, b) => b.created_at.localeCompare(a.created_at)],
  active: ["Last active", (a, b) => (b.last_active || "").localeCompare(a.last_active || "")],
  reports: ["Most reports", (a, b) => b.reports - a.reports],
};

const CSV_COLUMNS = [
  ["Name", (l) => l.name],
  ["Email", (l) => l.email],
  ["Organization", (l) => l.organization],
  ["Role searched", (l) => l.role],
  ["Location searched", (l) => l.location],
  ["Weekly attendance", (l) => l.attendance],
  ["Signed up", (l) => isoDate(l.created_at)],
  ["Last active", (l) => isoDate(l.last_active)],
  ["Hot lead", (l) => (l.hot ? "Yes" : "No")],
  ["Hot since", (l) => isoDate(l.hot_at)],
  ["Booked a call", (l) => (l.booked ? "Yes" : "No")],
  ["Reports viewed", (l) => l.reports],
  ["Actions recorded", (l) => l.events || 0],
];

const TOP = [
  { header: "Name", cell: (r) => placeName(r.name) },
  { header: "Leads", cell: (r) => count(r.leads), right: true, className: "num" },
];

function TopCard({ title, rows }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle><CardDescription>From each lead's latest search</CardDescription></CardHeader>
      <SimpleTable columns={TOP} rows={rows} rowKey={(r) => r.name} empty="No searches yet." />
    </Card>
  );
}

// Admin only (brief A3): everyone who signed up for a report, what they searched for, and a CSV export.
export default function LeadsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [hotOnly, setHotOnly] = useState(false);
  const [sort, setSort] = useState("newest");
  const [open, setOpen] = useState(null); // the email whose history is showing
  useEffect(() => { fetchLeads().then(setData).catch((e) => setError(`Couldn’t load leads (${e.message})`)); }, []);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const all = (data?.leads || []).filter((l) => !hotOnly || l.hot);
    const found = q ? all.filter((l) => [l.name, l.email, l.organization, l.role, l.location].some((v) => v?.toLowerCase().includes(q))) : all;
    return [...found].sort(SORTS[sort][1]);
  }, [data, query, hotOnly, sort]);

  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!data) return <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

  const t = data.totals;
  const exportCsv = () => downloadCsv(toCsv(shown, CSV_COLUMNS), `ministryhub-leads-${isoDate(new Date().toISOString())}.csv`);
  return (
    <>
      <Card className="kpis cost-kpis">
        <Kpi lead label="Total leads" value={count(t.total)} sub={`${count(t.organizations)} organizations`} />
        <Kpi label="Hot leads" value={count(t.hot)} sub="Viewed 3 or more reports" />
        <Kpi label="New this week" value={count(t.this_week)} sub={`${count(t.this_month)} this month`} />
        <Kpi label="Active this week" value={count(t.active_week)} sub="Leads who did anything in the last 7 days" />
      </Card>
      <div className="cost-grid">
        <TopCard title="Most searched roles" rows={data.by_role} />
        <TopCard title="Most searched locations" rows={data.by_location} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>All leads</CardTitle>
          <CardDescription>{query || hotOnly ? `${count(shown.length)} of ${count(data.leads.length)}` : `${count(data.leads.length)} leads`}</CardDescription>
          <CardAction className="flex flex-wrap justify-end gap-2">
            <Input type="search" aria-label="Search leads" placeholder="Search name, email, organization…" className="w-64"
              value={query} onChange={(e) => setQuery(e.target.value)} />
            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="w-40" aria-label="Sort leads"><SelectValue /></SelectTrigger>
              <SelectContent>{Object.entries(SORTS).map(([k, [label]]) => <SelectItem key={k} value={k}>{label}</SelectItem>)}</SelectContent>
            </Select>
            <Button variant={hotOnly ? "default" : "outline"} aria-pressed={hotOnly} onClick={() => setHotOnly(!hotOnly)}>
              <Flame aria-hidden="true" />Hot leads only
            </Button>
            <Button onClick={exportCsv} disabled={!shown.length}>
              <Download aria-hidden="true" />Export CSV
            </Button>
          </CardAction>
        </CardHeader>
        <SimpleTable columns={columns(setOpen)} rows={shown} rowKey={(l) => l.email}
          empty={query || hotOnly ? "No leads match." : "No one has signed up yet."} />
      </Card>
      <LeadHistory email={open} onClose={() => setOpen(null)} />
    </>
  );
}
