import React, { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { fetchLeads } from "@/api/admin.js";
import SimpleTable from "@/components/SimpleTable.jsx";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { downloadCsv, toCsv } from "@/lib/csv.js";
import { count, isoDate, longDate, when } from "@/lib/format.js";
import Kpi from "../components/Kpi.jsx";
import HotBadge, { BookedBadge, EmailBadge } from "./HotBadge.jsx";
import LeadHistory from "./LeadHistory.jsx";
import { ANY, NO_FILTERS, SHOW, SINCE, choices, filterLeads, isFiltered } from "./leadFilters.js";

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
          <EmailBadge status={l.report_email} />
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

const EMAIL_STATUS = { sent: "Sent", failed: "Failed", skipped: "Not sent" };

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
  ["Report email", (l) => EMAIL_STATUS[l.report_email] || ""],
  ["Reports viewed", (l) => l.reports],
  ["Actions recorded", (l) => l.events || 0],
];

const TOP = [
  { header: "Name", cell: (r) => placeName(r.name) },
  { header: "Leads", cell: (r) => count(r.leads), right: true, className: "num" },
];

// One filter: a labelled select. options: [[value, label], …]
function Pick({ label, value, onChange, options, className = "w-full sm:w-44" }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className={className} aria-label={label}><SelectValue /></SelectTrigger>
      <SelectContent>{options.map(([k, text]) => <SelectItem key={k} value={k}>{text}</SelectItem>)}</SelectContent>
    </Select>
  );
}

const labels = (obj) => Object.entries(obj).map(([k, [label]]) => [k, label]);

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
  const [filters, setFilters] = useState(NO_FILTERS);
  const [sort, setSort] = useState("newest");
  const [open, setOpen] = useState(null); // the email whose history is showing
  useEffect(() => { fetchLeads().then(setData).catch((e) => setError(`Couldn’t load leads (${e.message})`)); }, []);

  const shown = useMemo(() => filterLeads(data?.leads || [], filters).sort(SORTS[sort][1]), [data, filters, sort]);
  const setFilter = (key) => (value) => setFilters((f) => ({ ...f, [key]: value?.target ? value.target.value : value }));
  const filtered = isFiltered(filters);

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
          <CardDescription>{filtered ? `${count(shown.length)} of ${count(data.leads.length)}` : `${count(data.leads.length)} leads`}</CardDescription>
          <CardAction className="flex flex-wrap justify-end gap-2">
            <Input type="search" aria-label="Search leads" placeholder="Search name, email, organization…" className="w-64"
              value={filters.query} onChange={setFilter("query")} />
            <Pick label="Sort leads" value={sort} onChange={setSort} options={labels(SORTS)} className="w-40" />
            <Button onClick={exportCsv} disabled={!shown.length}>
              <Download aria-hidden="true" />Export CSV
            </Button>
          </CardAction>
        </CardHeader>
        <div className="mb-3 flex flex-wrap items-center gap-2" role="group" aria-label="Filter leads">
          <Pick label="Show leads" value={filters.show} onChange={setFilter("show")} options={labels(SHOW)} />
          <Pick label="Role searched" value={filters.role} onChange={setFilter("role")}
            options={[[ANY, "Any role"], ...choices(data.leads, "role").map((v) => [v, v])]} className="w-full sm:w-52" />
          <Pick label="Location searched" value={filters.location} onChange={setFilter("location")}
            options={[[ANY, "Any location"], ...choices(data.leads, "location").map((v) => [v, placeName(v)])]} />
          <Pick label="Signed up" value={filters.since} onChange={setFilter("since")}
            options={labels(SINCE).map(([k, t]) => [k, k === ANY ? "Signed up any time" : `Signed up: ${t.toLowerCase()}`])} className="w-full sm:w-52" />
          {filtered && <Button variant="link" onClick={() => setFilters(NO_FILTERS)}>Clear filters</Button>}
        </div>
        <SimpleTable columns={columns(setOpen)} rows={shown} rowKey={(l) => l.email}
          empty={filtered ? "No leads match these filters." : "No one has signed up yet."} />
      </Card>
      <LeadHistory email={open} onClose={() => setOpen(null)} />
    </>
  );
}
