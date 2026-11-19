import React, { useEffect, useState } from "react";
import { fetchRejected, restoreRejected } from "@/api/admin.js";
import SimpleTable from "@/components/SimpleTable.jsx";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { count, longDate } from "@/lib/format.js";
import FilterSelect from "../jobs/components/FilterSelect.jsx";

const SHOWN = 50; // rows at a time; "Show more" adds the next 50
const BY = { ai: "AI (daily feed)", "claude-review": "Claude review" };
const byLabel = (by) => BY[by] || by; // otherwise an admin's email

// Feed postings judged out of scope: not a church, Christian school or ministry, or a medical job. They are in no
// view or figure, and the daily feed skips them when they come again (server/app/jobs/repository.py).
export default function RejectedPage({ canEdit }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [by, setBy] = useState("");
  const [shown, setShown] = useState(SHOWN);
  const [version, setVersion] = useState(0);

  useEffect(() => { fetchRejected().then((d) => { setData(d); setError(null); }).catch((e) => setError(`Couldn’t load the rejected jobs (${e.message})`)); }, [version]);
  useEffect(() => setShown(SHOWN), [search, by]);

  if (error && !data) return <p className="form-error" role="alert">{error}</p>;
  if (!data) return <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

  const q = search.trim().toLowerCase();
  const rows = data.rows.filter((r) => (!by || r.rejected_by === by || (by === "admin" && !BY[r.rejected_by]))
    && (!q || [r.job_name, r.company_name, r.reason].some((v) => (v || "").toLowerCase().includes(q))));
  const include = (id) => restoreRejected(id).then(() => setVersion((v) => v + 1)).catch((e) => setError(e.message));

  const columns = [
    { header: "Job", className: "min-w-[200px] whitespace-normal", cell: (r) => (
      <>
        {r.post_url ? <a href={r.post_url} target="_blank" rel="noopener noreferrer">{r.job_name || "Untitled"}</a> : r.job_name}
        <div className="muted small">{[r.company_name, r.city, r.region].filter(Boolean).join(" · ")}</div>
      </>
    ) },
    { header: "Why it was rejected", className: "min-w-[220px] whitespace-normal", cell: (r) => r.reason },
    { header: "Rejected by", cell: (r) => <>{byLabel(r.rejected_by)}<div className="muted small">{longDate(r.rejected_at)}</div></> },
    ...(canEdit ? [{ header: "", right: true, cell: (r) => (
      <Button variant="outline" size="sm" onClick={() => include(r.post_uuid)}>Include again</Button>
    ) }] : []),
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rejected jobs</CardTitle>
        <CardDescription className="whitespace-normal">
          Feed postings that aren’t at a church, Christian school or ministry, or are medical jobs. They are left out of
          every view and figure, and the daily feed skips them when they come again. Include one again if the call was wrong.
        </CardDescription>
      </CardHeader>
      <div className="grid gap-3 px-6">
        <div className="flex flex-wrap items-end gap-2">
          <Input type="search" aria-label="Search job, employer or reason" placeholder="Search job, employer or reason"
            className="w-72" value={search} onChange={(e) => setSearch(e.target.value)} />
          <FilterSelect id="rejected-by" label="Rejected by" value={by} onChange={setBy} all="Anyone"
            options={[["ai", BY.ai], ["claude-review", BY["claude-review"]], ["admin", "An admin"]]} />
          <span className="num text-sm" aria-live="polite">{count(rows.length)} of {count(data.total)} rejected jobs</span>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <SimpleTable columns={columns} rows={rows.slice(0, shown)} rowKey={(r) => r.post_uuid}
          empty={data.total ? "No rejected jobs match." : "No jobs have been rejected."} />
        {rows.length > shown && (
          <Button variant="outline" className="justify-self-center" onClick={() => setShown((n) => n + SHOWN)}>
            Show {Math.min(SHOWN, rows.length - shown)} more
          </Button>
        )}
      </div>
    </Card>
  );
}
