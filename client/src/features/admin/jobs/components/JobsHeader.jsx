import React from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { count, longDate } from "@/lib/format.js";
import Finding from "./Finding.jsx";

// Title, data freshness, the one-sentence answer, and the CSV export.
export default function JobsHeader({ source, sources, filters, stats: s, onExport, canExport }) {
  const labels = source.map((key) => sources?.find((x) => x.key === key)?.label).filter(Boolean).join(" + ");
  return (
    <div className="title-row">
      <div>
        <h1>Jobs by source</h1>
        <p className="muted small">
          {labels || "…"} · {source.includes("json") ? "data as of" : "pages last read"} {s?.as_of ? longDate(s.as_of) : "…"}
        </p>
        <div className="finding" aria-live="polite">
          {s ? <Finding filters={filters} stats={s} /> : <Skeleton className="h-4 w-[min(520px,100%)]" />}
        </div>
      </div>
      <Button onClick={onExport} disabled={!canExport || !s?.postings}>
        <Download aria-hidden="true" />
        Export {s ? count(s.postings) : ""} postings
      </Button>
    </div>
  );
}
