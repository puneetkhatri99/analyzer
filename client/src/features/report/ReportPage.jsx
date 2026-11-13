import React, { useEffect, useState } from "react";
import CallBand from "@/features/site/CallBand.jsx";
import PublicLayout from "@/features/site/PublicLayout.jsx";
import { savedLead } from "@/features/site/lead.js";
import { HOW_URL } from "@/features/site/links.js";
import { useReveal } from "@/lib/motion.js";
import Breakdowns from "./components/Breakdowns.jsx";
import InsightCard from "./components/InsightCard.jsx";
import MarketStats from "./components/MarketStats.jsx";
import OfferCheck from "./components/OfferCheck.jsx";
import PayCard from "./components/PayCard.jsx";
import PrintReport from "./components/PrintReport.jsx";
import ReportHeader from "./components/ReportHeader.jsx";
import RefinePanel from "./components/refine/RefinePanel.jsx";
import WidenedNote from "./components/WidenedNote.jsx";
import { PART_TIME } from "./lib/filters.js";
import { useReport } from "./hooks/useReport.js";
import { useReportOptions } from "./hooks/useReportOptions.js";

function ReportBody({ r, roleText, typeLabel }) {
  return (
    <>
      {r.note && r.pay && <WidenedNote note={r.note} />}
      <PayCard r={r} typeLabel={typeLabel} />
      <MarketStats r={r} roleText={roleText} />
      {r.pay && <OfferCheck key={`${r.unit}-${r.pay.typical}`} r={r} />}
      <Breakdowns r={r} />
      <InsightCard insight={r.insight} roleText={roleText} />
      <CallBand title={`Hiring for ${r.title.role}?`} secondary={<a className="mh-band-link" href={HOW_URL}>See how our searches work</a>}>
        Let's talk through your search in {r.title.area}. A responsive partner from first call to first day:
        we reply promptly, update you every two weeks, and never go quiet.
      </CallBand>
    </>
  );
}

export default function ReportPage() {
  const [lead] = useState(savedLead);
  const { options } = useReportOptions();
  const { filters, setFilters, report: r, error, updating } = useReport();

  // shortcut: the sign-up gate is in the browser only; the report API returns summary figures, nothing private
  useEffect(() => { if (!lead) window.location.replace("/"); }, [lead]);
  useReveal(r);
  if (!lead) return null;

  const roleText = r ? r.title.role : "these";
  const typeLabel = filters.type === PART_TIME ? "part-time" : "full-time";
  return (
    <PublicLayout after={r && <PrintReport r={r} lead={lead} roleText={roleText} typeLabel={typeLabel} />}>
      <div className="mh-wrap mh-report">
        <ReportHeader r={r} />
        <div className="mh-report-grid">
          {options ? <RefinePanel f={filters} opts={options} setF={setFilters} /> : <aside className="mh-refine" />}
          <div className={`mh-report-main${updating && r ? " is-updating" : ""}`} aria-live="polite" aria-busy={updating}>
            {error && <p className="mh-note" role="alert">We couldn't load the report ({error}). Please try again in a minute.</p>}
            {r && <ReportBody r={r} roleText={roleText} typeLabel={typeLabel} />}
          </div>
        </div>
      </div>
    </PublicLayout>
  );
}
