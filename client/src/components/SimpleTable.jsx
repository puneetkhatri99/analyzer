import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// A read-only table from column definitions: { header, cell: row => node, right?, className? }.
// For sorting and paging, use TanStack (see features/admin/jobs/components/JobsTable.jsx).
export default function SimpleTable({ columns, rows, rowKey, empty }) {
  if (!rows.length && empty) return <p className="empty-line">{empty}</p>;
  const cellClass = (c) => [c.right && "text-right", c.className].filter(Boolean).join(" ") || undefined;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((c) => <TableHead key={c.header} className={c.right ? "text-right" : undefined}>{c.header}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => (
          <TableRow key={rowKey ? rowKey(row) : i}>
            {columns.map((c) => <TableCell key={c.header} className={cellClass(c)}>{c.cell(row)}</TableCell>)}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
