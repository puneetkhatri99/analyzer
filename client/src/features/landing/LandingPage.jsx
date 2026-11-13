import React from "react";
import CallBand from "@/features/site/CallBand.jsx";
import PublicLayout from "@/features/site/PublicLayout.jsx";
import { useReportOptions } from "@/features/report/hooks/useReportOptions.js";
import { useReveal } from "@/lib/motion.js";
import HeroCopy from "./HeroCopy.jsx";
import LeadForm from "./LeadForm.jsx";
import MarketGlance from "./MarketGlance.jsx";
import ReportFeatures from "./ReportFeatures.jsx";

export default function LandingPage() {
  const { options, error } = useReportOptions();
  useReveal(options);
  return (
    <PublicLayout>
      <section className="mh-wrap mh-hero">
        <HeroCopy landing={options?.landing} />
        <LeadForm options={options} />
      </section>
      {error && <p className="mh-wrap mh-error" role="alert">{error}</p>}
      <MarketGlance landing={options?.landing} />
      <ReportFeatures />
      <div className="mh-wrap mh-section-tight">
        <CallBand title="Hiring soon?">
          Let's talk through your search. MinistryHub equips churches and faith-based nonprofits to build
          world-changing staff teams. Grab a spot on Jordan's calendar for a search strategy consultation.
        </CallBand>
      </div>
    </PublicLayout>
  );
}
