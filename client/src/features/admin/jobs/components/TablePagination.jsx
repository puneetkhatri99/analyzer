import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const PAGE_SIZES = [25, 50, 100];

// Rows per page, "1–25 of 1,840", previous and next. `table` is a TanStack table with pagination.
export default function TablePagination({ table, total }) {
  const { pageIndex, pageSize } = table.getState().pagination;
  const from = pageIndex * pageSize + 1;
  return (
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
        <Button variant="outline" size="icon-sm" aria-label="Previous page" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
          <ChevronLeft />
        </Button>
        <Button variant="outline" size="icon-sm" aria-label="Next page" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
