import React, { useEffect, useState } from "react";
import { flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import { ORIGINS, isoDate, listedPay } from "../format.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const Dash = () => <span className="dash">—</span>;
const location = (d) => [d.city, d.region].filter(Boolean).join(", ") || d.country || "";
const payText = (d) => {
  const p = listedPay(d);
  return p ? `${p.amount} ${p.unit}` : "";
};
const statusText = (d) => (d.status === "expired" ? `Expired ${isoDate(d.expired_at)}` : d.status === "open" ? "Open" : "Not verified");

// Narrow screens hide the less important columns, widest-needed last (same order Tabulator used).
const HIDE = { 1: "hidden sm:table-cell", 2: "hidden md:table-cell", 3: "hidden lg:table-cell", 4: "hidden 2xl:table-cell" };

function Status({ d }) {
  if (d.status === "expired") {
    return <Badge variant="outline" className="border-transparent px-0 text-destructive" title={d.last_live_at ? `Last seen open ${isoDate(d.last_live_at)}` : "Never seen open"}>
      Expired <span className="num">{isoDate(d.expired_at)}</span></Badge>;
  }
  if (d.status === "open") return <Badge variant="secondary" title={`Checked open on ${isoDate(d.last_live_at)}`}>Open</Badge>;
  return <Badge variant="outline" className="text-muted-foreground" title="The job page couldn't be read, so it isn't known whether it's still open">Not verified</Badge>;
}

const COLUMNS = [
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

const PAGE_SIZES = [25, 50, 100];

export default function JobsTable({ rows, onReady, onOpen }) {
  const [sorting, setSorting] = useState([{ id: "posted", desc: true }]);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 25 });
  const table = useReactTable({
    data: rows,
    columns: COLUMNS,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getRowId: (d) => d.post_uuid,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    sortDescFirst: false,
    enableSortingRemoval: false,
  });

  useEffect(() => { onReady?.(table); }, [table, onReady]);
  // new filter results start on the first page
  useEffect(() => { setPagination((p) => ({ ...p, pageIndex: 0 })); }, [rows]);

  const total = rows.length;
  const { pageIndex, pageSize } = pagination;
  const from = pageIndex * pageSize + 1;
  const cls = (meta = {}) => [HIDE[meta.hide], meta.right && "text-right", meta.className].filter(Boolean).join(" ");

  return (
    <div className="jobs-table">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((g) => (
            <TableRow key={g.id} className="hover:bg-transparent">
              {g.headers.map((h) => {
                const dir = h.column.getIsSorted();
                const Arrow = dir === "asc" ? ArrowUp : ArrowDown;
                return (
                  <TableHead key={h.id} className={cls(h.column.columnDef.meta)} aria-sort={dir ? (dir === "asc" ? "ascending" : "descending") : undefined}>
                    <button type="button" className={`sort-btn${h.column.columnDef.meta?.right ? " flex-row-reverse" : ""}`} onClick={h.column.getToggleSortingHandler()}>
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      <Arrow className={`size-3 ${dir ? "" : "invisible"}`} aria-hidden="true" />
                    </button>
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className="cursor-pointer" onClick={() => onOpen?.(row.original)}>
              {row.getVisibleCells().map((c) => (
                <TableCell key={c.id} className={`py-2.5 align-top ${cls(c.column.columnDef.meta)}`}>{flexRender(c.column.columnDef.cell, c.getContext())}</TableCell>
              ))}
            </TableRow>
          ))}
          {total === 0 && (
            <TableRow className="hover:bg-transparent"><TableCell colSpan={COLUMNS.length} className="py-10 text-center text-muted-foreground">No postings match these filters.</TableCell></TableRow>
          )}
        </TableBody>
      </Table>

      {total > 0 && (
        <div className="jobs-table-foot">
          <div className="hidden items-center gap-2 sm:flex">
            <span>Rows per page</span>
            <Select value={String(pageSize)} onValueChange={(v) => table.setPageSize(Number(v))}>
              <SelectTrigger size="sm" aria-label="Rows per page"><SelectValue /></SelectTrigger>
              <SelectContent>{PAGE_SIZES.map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <span className="num" aria-live="polite">{from}–{Math.min(from + pageSize - 1, total)} of {total.toLocaleString("en-US")}</span>
          <div className="flex gap-1.5">
            <Button variant="outline" size="icon-sm" aria-label="Previous page" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}><ChevronLeft /></Button>
            <Button variant="outline" size="icon-sm" aria-label="Next page" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}><ChevronRight /></Button>
          </div>
        </div>
      )}
    </div>
  );
}
