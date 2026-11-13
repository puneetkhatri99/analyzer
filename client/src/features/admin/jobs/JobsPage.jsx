import React, { useState } from "react";
import { deleteJob } from "@/api/admin.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadCsv, toCsv } from "@/lib/csv.js";
import { count } from "@/lib/format.js";
import BenchmarkGrid from "./components/BenchmarkGrid.jsx";
import FilterBar from "./components/FilterBar.jsx";
import JobDetail from "./components/JobDetail.jsx";
import JobsHeader from "./components/JobsHeader.jsx";
import JobsTable, { CSV_COLUMNS } from "./components/JobsTable.jsx";
import KpiStrip from "./components/KpiStrip.jsx";
import SourceTabs from "./components/SourceTabs.jsx";
import { useJobsData } from "./hooks/useJobsData.js";

// Admin only (brief A1, A2): every posting per source, with its pay benchmarks, source and link.
export default function JobsPage({ canEdit = false }) {
  const d = useJobsData();
  const [table, setTable] = useState(null);
  const [openJob, setOpenJob] = useState(null);
  const s = d.summary?.stats;

  // every matching posting, in the table's current sort order
  const exportCsv = () => downloadCsv(toCsv(table.getSortedRowModel().rows.map((r) => r.original), CSV_COLUMNS),
    `ministry-jobs-${d.source}-${new Date().toISOString().slice(0, 10)}.csv`);
  const removeJob = () => deleteJob(d.source, openJob.post_uuid).then(() => { setOpenJob(null); d.reload(); });
  const focusRow = (id) => document.querySelector(`button.job-title[data-id="${CSS.escape(id)}"]`)?.focus();

  return (
    <>
      <SourceTabs sources={d.sources} value={d.source} onChange={d.changeSource} />
      <JobsHeader source={d.source} sources={d.sources} filters={d.filters} stats={s} onExport={exportCsv} canExport={!!table} />
      <FilterBar filters={d.filters} setFilter={d.setFilter} clearFilter={d.clearFilter} resetFilters={d.resetFilters}
        options={d.options} showChurchSize={d.source !== "nonprofits"} />

      {d.error ? (
        <Alert variant="destructive">
          <AlertTitle>Couldn’t load the benchmarks.</AlertTitle>
          <AlertDescription>
            The server didn’t answer ({d.error}). It may be waking up; try again in a minute.
            <Button variant="outline" size="sm" className="mt-2 text-foreground" onClick={d.reload}>Retry</Button>
          </AlertDescription>
        </Alert>
      ) : (
        <div className={`dash-grid${d.updating && d.summary ? " is-updating" : ""}`} aria-busy={d.updating}>
          <div className="span-12"><KpiStrip stats={s} loading={!s} /></div>
          <BenchmarkGrid summary={d.summary} filters={d.filters} setFilter={d.setFilter} isChurch={d.source !== "nonprofits"} />
          <Card as="section" className="table-card span-12" aria-labelledby="h-postings">
            <CardHeader>
              <CardTitle id="h-postings">Postings</CardTitle>
              <CardDescription>{s ? `${count(s.postings)} matching` : ""}</CardDescription>
            </CardHeader>
            <JobsTable rows={d.rows} onReady={setTable} onOpen={setOpenJob} />
          </Card>
        </div>
      )}

      {openJob && (
        <JobDetail job={openJob} onClose={() => setOpenJob(null)} onDelete={canEdit ? removeJob : null}
          returnFocus={() => focusRow(openJob.post_uuid)} />
      )}
    </>
  );
}
