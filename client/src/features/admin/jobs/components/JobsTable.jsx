import React, { useEffect, useState } from "react";
import { flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { COLUMNS, HIDE } from "./jobColumns.jsx";
import TablePagination from "./TablePagination.jsx";

export { CSV_COLUMNS } from "./jobColumns.jsx";

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

      {total > 0 && <TablePagination table={table} total={total} />}
    </div>
  );
}
