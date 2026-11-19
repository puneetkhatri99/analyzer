import React, { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import { deleteCostCalls, deleteMatchingCostCalls, fetchCostCalls } from "@/api/admin.js";
import Confirm from "@/components/Confirm.jsx";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { count, when } from "@/lib/format.js";
import FilterSelect from "../jobs/components/FilterSelect.jsx";
import { purpose as purposeLabel, usd } from "./costFormat.js";

const EMPTY = { purpose: "", run: "", date_from: "", date_to: "", q: "" };

// The AI calls, 25 a page, with filters. Admins can delete selected calls, or every call matching the filters.
// The totals above are summed from the same rows, so `onChanged` reloads them.
export default function CallsTable({ purposes, runs, version, onChanged }) {
  const [filters, setFilters] = useState(EMPTY);
  const [search, setSearch] = useState(""); // the URL box; applied after a pause so each key isn't a request
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null); // { rows, total, cost, page_size }
  const [selected, setSelected] = useState(() => new Set());
  const [error, setError] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => (f.q === search.trim() ? f : { ...f, q: search.trim() })), 400);
    return () => clearTimeout(timer);
  }, [search]);
  useEffect(() => { setPage(1); }, [filters]);
  useEffect(() => { setSelected(new Set()); }, [filters, page]); // picks are per page: the shown cost sums this page only
  useEffect(() => {
    let current = true;
    fetchCostCalls(filters, page)
      .then((d) => { if (!current) return; if (!d.rows.length && page > 1) setPage(1); else { setData(d); setError(null); } })
      .catch((e) => current && setError(`Couldn’t load the calls (${e.message})`));
    return () => { current = false; };
  }, [filters, page, version]);

  const set = (key) => (value) => setFilters((f) => ({ ...f, [key]: value }));
  const filtered = Object.values(filters).some(Boolean);
  const reset = () => { setFilters(EMPTY); setSearch(""); };

  const rows = data?.rows || [];
  const size = data?.page_size || 25;
  const from = (page - 1) * size + 1;
  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.id));
  const toggle = (id) => setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const togglePage = () => setSelected(allOnPage ? new Set() : new Set(rows.map((r) => r.id)));
  const selectedCost = rows.filter((r) => selected.has(r.id)).reduce((sum, r) => sum + Number(r.cost_usd || 0), 0);

  const remove = (action) => action().then(() => { setSelected(new Set()); onChanged(); }).catch((e) => setError(e.message));

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-end gap-2">
        <FilterSelect id="calls-purpose" label="Purpose" value={filters.purpose} onChange={set("purpose")} all="All purposes"
          options={purposes.map((p) => [p, purposeLabel(p)])} />
        <FilterSelect id="calls-run" label="Run" value={filters.run} onChange={set("run")} all="All runs"
          options={[["none", "Not from a feed run"], ...runs.map((r) => [r, r])]} />
        <label className="grid gap-1 text-xs text-muted-foreground">From
          <Input type="date" className="w-40" value={filters.date_from} onChange={(e) => set("date_from")(e.target.value)} />
        </label>
        <label className="grid gap-1 text-xs text-muted-foreground">To
          <Input type="date" className="w-40" value={filters.date_to} onChange={(e) => set("date_to")(e.target.value)} />
        </label>
        <Input type="search" aria-label="Search the job URL" placeholder="Search the job URL" className="w-56" value={search}
          onChange={(e) => setSearch(e.target.value)} />
        {(filtered || search) && <Button variant="ghost" onClick={reset}>Clear filters</Button>}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="num" aria-live="polite">
          {data ? `${count(data.total)} call${data.total === 1 ? "" : "s"}${filtered ? " match" : ""} · ${usd(data.cost)}` : "Loading…"}
        </span>
        {selected.size > 0 && (
          <Confirm title={`Delete ${selected.size} AI call${selected.size === 1 ? "" : "s"}?`} action="Delete"
            description={`This removes ${usd(selectedCost)} from every total on this page. It can’t be undone.`}
            onConfirm={() => remove(() => deleteCostCalls([...selected]))}>
            <Button variant="destructive" size="sm"><Trash2 aria-hidden="true" />Delete selected ({selected.size})</Button>
          </Confirm>
        )}
        {data?.total > 0 && (
          <Confirm title={`Delete ${count(data.total)} AI call${data.total === 1 ? "" : "s"}?`} action="Delete all"
            description={`${filtered ? "Every call that matches the filters" : "Every AI call"} (${usd(data.cost)} in total) is removed from the log and from every total on this page. It can’t be undone.`}
            onConfirm={() => remove(() => deleteMatchingCostCalls(filters))}>
            <Button variant="outline" size="sm"><Trash2 aria-hidden="true" />{filtered ? "Delete all matching" : "Delete all"}</Button>
          </Confirm>
        )}
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {data && !rows.length ? <p className="empty-line">{filtered ? "No AI calls match these filters." : "No AI calls yet."}</p> : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"><Checkbox aria-label="Select all on this page" checked={allOnPage} onCheckedChange={togglePage} /></TableHead>
              <TableHead>When</TableHead>
              <TableHead>Purpose</TableHead>
              <TableHead>Run</TableHead>
              <TableHead>Job URL</TableHead>
              <TableHead className="text-right">Tokens in / out</TableHead>
              <TableHead className="text-right">Searches</TableHead>
              <TableHead className="text-right">Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id} data-state={selected.has(r.id) ? "selected" : undefined}>
                <TableCell><Checkbox aria-label={`Select the call from ${when(r.created_at)}`} checked={selected.has(r.id)} onCheckedChange={() => toggle(r.id)} /></TableCell>
                <TableCell>{when(r.created_at)}</TableCell>
                <TableCell>{purposeLabel(r.purpose)}</TableCell>
                <TableCell className="muted">{r.run_id || r.admin_email || "—"}</TableCell>
                <TableCell className="url-cell"><a href={r.url} target="_blank" rel="noopener noreferrer" title={r.url}>{r.url}</a></TableCell>
                <TableCell className="num text-right">{count(r.input_tokens)} / {count(r.output_tokens)}</TableCell>
                <TableCell className="num text-right">{r.web_searches}</TableCell>
                <TableCell className="num text-right">{r.cost_usd == null ? "—" : usd(r.cost_usd)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {data?.total > size && (
        <div className="jobs-table-foot">
          <span className="num" aria-live="polite">{from}–{Math.min(from + size - 1, data.total)} of {count(data.total)}</span>
          <div className="flex gap-1.5">
            <Button variant="outline" size="icon-sm" aria-label="Previous page" onClick={() => setPage(page - 1)} disabled={page <= 1}><ChevronLeft /></Button>
            <Button variant="outline" size="icon-sm" aria-label="Next page" onClick={() => setPage(page + 1)} disabled={from + size > data.total}><ChevronRight /></Button>
          </div>
        </div>
      )}
    </div>
  );
}
