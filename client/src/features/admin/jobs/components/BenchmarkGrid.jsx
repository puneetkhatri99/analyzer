import React from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MIN_PAID, count } from "@/lib/format.js";
import BreakdownList from "./BreakdownList.jsx";
import PayDistribution from "./PayDistribution.jsx";
import PayLadder from "./PayLadder.jsx";

function Section({ id, title, meta, className, aside, children }) {
  return (
    <Card as="section" className={className} aria-labelledby={id}>
      <CardHeader><CardTitle id={id}>{title}</CardTitle>{aside}{meta && <CardDescription>{meta}</CardDescription>}</CardHeader>
      {children}
    </Card>
  );
}

function LoadingCard({ className, title, rows = 12 }) {
  return (
    <Card className={className} aria-busy="true">
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-8 items-center"><Skeleton className="h-2.5" style={{ width: `${90 - i * 8}%` }} /></div>
      ))}
    </Card>
  );
}

const Legend = () => (
  <div className="legend" aria-hidden="true"><span><i className="sw-band" />Middle half</span><span><i className="sw-tick" />Median</span></div>
);

// Pay by role, state, church size and denomination, and how pay is spread. Clicking a row filters by it.
export default function BenchmarkGrid({ summary, filters, setFilter, isChurch }) {
  if (!summary) {
    return <><LoadingCard className="span-7" title="Pay by role" /><LoadingCard className="span-5" title="Pay by state" /></>;
  }
  const s = summary.stats;
  return (
    <>
      <Section id="h-role" title="Pay by role" className="span-7" aside={<Legend />}>
        <PayLadder rows={summary.by_role} nameHeader="Role" selected={filters.role} onSelect={(v) => setFilter("role", v)} />
        <p className="card-note">Annual pay; hourly roles counted at 2,080 hours. Role is matched from the job title. Roles with fewer than {MIN_PAID} paid postings aren’t benchmarked.</p>
      </Section>
      <div className="stack span-5">
        <Section id="h-state" title="Pay by state" meta="Top 10 by postings">
          <PayLadder compact rows={summary.by_state} nameHeader="State" selected={filters.region} onSelect={(v) => setFilter("region", v)} />
        </Section>
        {isChurch && (
          <Section id="h-size" title="By church size" meta="Weekly attendance">
            <BreakdownList rows={summary.by_church_size.filter((r) => r.postings > 0)} nameHeader="Attendance" />
            <p className="card-note">{count(s.no_church_size)} of {count(s.postings)} postings don’t state church size.</p>
          </Section>
        )}
      </div>
      <Section id="h-dist" title="How pay is spread" meta={`${count(s.paid)} postings with pay`} className="span-7 fill">
        {s.paid > 0
          ? <PayDistribution histogram={summary.histogram} bin={summary.histogram_bin} cap={summary.histogram_cap} median={s.median} />
          : <p className="empty-line">None of the matching postings list pay.</p>}
      </Section>
      <Section id="h-denom" title="By denomination" meta={`${count(summary.by_denomination.length)} stated`} className="span-5">
        <BreakdownList rows={summary.by_denomination} nameHeader="Denomination" limit={7} selected={filters.denomination}
          onSelect={(v) => setFilter("denomination", v)} />
        <p className="card-note">{count(s.no_denomination)} of {count(s.postings)} postings don’t state a denomination.</p>
      </Section>
    </>
  );
}
