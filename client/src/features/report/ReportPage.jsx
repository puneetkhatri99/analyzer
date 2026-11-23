import React, { useEffect, useState } from "react";
import CallBand from "@/features/site/CallBand.jsx";
import PublicLayout from "@/features/site/PublicLayout.jsx";
import { savedLead, track } from "@/features/site/lead.js";
import { HOW_URL } from "@/features/site/links.js";
import { useReveal } from "@/lib/motion.js";
import Breakdowns from "./components/Breakdowns.jsx";
import MarketStats from "./components/MarketStats.jsx";
import OfferCheck from "./components/OfferCheck.jsx";
import PayCard from "./components/PayCard.jsx";
import PrintReport from "./components/PrintReport.jsx";
import ReportHeader from "./components/ReportHeader.jsx";
import RefinePanel from "./components/refine/RefinePanel.jsx";
import MergedNote from "./components/MergedNote.jsx";
import { PART_TIME } from "./lib/filters.js";
import { useReport } from "./hooks/useReport.js";
import { useReportOptions } from "./hooks/useReportOptions.js";

function ReportBody({ r, roleText, typeLabel }) {
  return (
    <>
      {r.merged?.length > 0 && r.pay && <MergedNote merged={r.merged} />}
      <PayCard r={r} typeLabel={typeLabel} />
      {r.pay && <OfferCheck key={`${r.unit}-${r.pay.typical}`} r={r} />}
      <MarketStats r={r} roleText={roleText} />
      <Breakdowns r={r} />
      <CallBand title={`Hiring for ${r.title.role}?`} secondary={<a className="mh-band-link" href={HOW_URL} data-track>See how our searches work</a>}>
        Let's talk through your search in {r.title.area}. A responsive partner from first call to first day:
        we reply promptly, update you every two weeks, and never go quiet.
      </CallBand>
    </>
  );
}

export default function ReportPage() {
  const [lead] = useState(savedLead);
  const { options } = useReportOptions();
  const { filters, draft, setDraft, apply, reset, pending, changed, report: r, error, updating } = useReport();

  // Not signed up (e.g. opened a shared link): sign up first, then come back to this exact report.
  // shortcut: the sign-up gate is in the browser only; the report API returns summary figures, nothing private
  useEffect(() => {
    if (!lead) window.location.replace(`/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
  }, [lead]);
  useEffect(() => {
    if (!r) return undefined;
    const downloaded = () => track("download", { report: `${r.title.role} in ${r.title.area}` });
    window.addEventListener("beforeprint", downloaded);
    return () => window.removeEventListener("beforeprint", downloaded);
  }, [r]);
  useReveal(r);
  if (!lead) return null;

  const roleText = r ? r.title.role : "these";
  const typeLabel = filters.type === PART_TIME ? "part-time" : "full-time";
  return (
    <PublicLayout after={r && <PrintReport r={r} roleText={roleText} typeLabel={typeLabel} />}>
      <div className="mh-wrap mh-report">
        <ReportHeader r={r} />
        <div className="mh-report-grid">
          {options ? <RefinePanel f={draft} opts={options} setF={setDraft} apply={apply} pending={pending} reset={reset} changed={changed} /> : <aside className="mh-refine" />}
          <div className={`mh-report-main${updating && r ? " is-updating" : ""}`} aria-live="polite" aria-busy={updating}>
            {error && <p className="mh-note" role="alert">We couldn't load the report ({error}). Please try again in a minute.</p>}
            {r && <ReportBody r={r} roleText={roleText} typeLabel={typeLabel} />}
          </div>
        </div>
      </div>
    </PublicLayout>
  );
}
