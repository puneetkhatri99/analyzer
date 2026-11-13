import React from "react";
import { Badge } from "@/components/ui/badge";
import { ORIGINS, isoDate, listedPay } from "@/lib/format.js";

const Dash = () => <span className="dash">—</span>;
const location = (d) => [d.city, d.region].filter(Boolean).join(", ") || d.country || "";
const payText = (d) => {
  const p = listedPay(d);
  return p ? `${p.amount} ${p.unit}` : "";
};
const statusText = (d) => (d.status === "expired" ? `Expired ${isoDate(d.expired_at)}` : d.status === "open" ? "Open" : "Not verified");

// Narrow screens hide the less important columns, widest-needed last (same order Tabulator used).
export const HIDE = { 1: "hidden sm:table-cell", 2: "hidden md:table-cell", 3: "hidden lg:table-cell", 4: "hidden 2xl:table-cell" };

function Status({ d }) {
  if (d.status === "expired") {
    return <Badge variant="outline" className="border-transparent px-0 text-destructive" title={d.last_live_at ? `Last seen open ${isoDate(d.last_live_at)}` : "Never seen open"}>
      Expired <span className="num">{isoDate(d.expired_at)}</span></Badge>;
  }
  if (d.status === "open") return <Badge variant="secondary" title={`Checked open on ${isoDate(d.last_live_at)}`}>Open</Badge>;
  return <Badge variant="outline" className="text-muted-foreground" title="The job page couldn't be read, so it isn't known whether it's still open">Not verified</Badge>;
}

export const COLUMNS = [
  {
    id: "job", header: "Job", accessorKey: "job_name", meta: { className: "min-w-[200px] whitespace-normal [overflow-wrap:anywhere]" },
    cell: ({ row: { original: d } }) => (
      <>
        {/* a button so keyboard users can open the details too; the click bubbles to the row */}
        <button type="button" className="job-title" data-id={d.post_uuid}>{d.job_name || "Untitled role"}</button>
        <div className="job-sub">{d.company_name || "Employer not stated"}</div>
      </>
    ),
  },
  { id: "role", header: "Role", accessorKey: "role", meta: { hide: 2, className: "max-w-[170px] truncate" }, cell: ({ getValue }) => <span title={getValue()}>{getValue() || <Dash />}</span> },
  { id: "denomination", header: "Denomination", accessorKey: "denomination", meta: { hide: 4, className: "max-w-[160px] truncate" }, cell: ({ getValue }) => <span title={getValue()}>{getValue() || <Dash />}</span> },
  { id: "location", header: "Location", accessorFn: location, meta: { hide: 1, className: "max-w-[170px] truncate" }, cell: ({ getValue }) => <span title={getValue()}>{getValue() || <Dash />}</span> },
  {
    id: "pay", header: "Pay", accessorFn: (d) => d.salary_annual_mid ?? undefined, sortUndefined: "last", meta: { right: true, className: "min-w-[120px] whitespace-normal" },
    cell: ({ row: { original: d } }) => {
      const p = listedPay(d);
      return p ? <><span className="num">{p.amount}</span><span className="pay-unit">{p.unit}</span></> : <Dash />;
    },
  },
  { id: "status", header: "Status", accessorKey: "status", meta: { hide: 3 }, cell: ({ row: { original: d } }) => <Status d={d} /> },
  {
    id: "origin", header: "Added via", accessorKey: "origin", meta: { hide: 2 },
    cell: ({ row: { original: d } }) => <span className="origin" title={`Added ${isoDate(d.added_at)}`}>{ORIGINS[d.origin] || d.origin}</span>,
  },
  { id: "hours", header: "Type", accessorKey: "hours", meta: { hide: 3 }, cell: ({ getValue }) => getValue() || <Dash /> },
  { id: "posted", header: "Posted", accessorKey: "first_indexed", meta: { hide: 2, right: true }, cell: ({ getValue }) => <span className="num">{isoDate(getValue())}</span> },
];

// The CSV export: every column, including the employer and link the table only shows in the detail view.
export const CSV_COLUMNS = [
  ["Job", (d) => d.job_name],
  ["Role", (d) => d.role],
  ["Denomination", (d) => d.denomination],
  ["Location", location],
  ["Pay", payText],
  ["Status", statusText],
  ["Added via", (d) => ORIGINS[d.origin] || d.origin],
  ["Type", (d) => d.hours],
  ["Posted", (d) => isoDate(d.first_indexed)],
  ["Employer", (d) => d.company_name],
  ["Link", (d) => d.post_url],
];
