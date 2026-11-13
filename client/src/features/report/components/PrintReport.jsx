import React from "react";
import { Card } from "@/components/ui/card";
import { BOOK_URL } from "@/features/site/links.js";
import { longDay } from "@/lib/format.js";
import BarList from "./BarList.jsx";
import InsightCard from "./InsightCard.jsx";
import MarketStats from "./MarketStats.jsx";
import PayCard from "./PayCard.jsx";

// The branded export (brief P8): shown only when printing, so "Download report" saves it as a PDF.
export default function PrintReport({ r, lead, roleText, typeLabel }) {
  return (
    <div className="mh-print" aria-hidden="true">
      <div className="mh-print-head">
        <img className="mh-logo" src="/ministryhub-logo.png" alt="" />
        <div><p className="mh-eyebrow">Market Analysis Report</p><p>{longDay(new Date().toISOString())}</p></div>{/* taste-skill-ignore: label in the client's approved design */}
      </div>
      <h1>{r.title.role} pay in <span className="mh-underline">{r.title.area}</span></h1>
      {lead && <p className="mh-print-for">Prepared for {lead.name}, {lead.organization}</p>}
      <PayCard r={r} typeLabel={typeLabel} />
      <MarketStats r={r} roleText={roleText} compact />
      <div className="mh-print-cols">
        <Card className="mh-card"><h2>Compared with other roles</h2><BarList rows={r.by_role} selected={r.filters.role} unit={r.unit} /></Card>
        <Card className="mh-card"><h2>By weekly attendance</h2><BarList rows={r.by_size} selected={r.filters.size} unit={r.unit} /></Card>
      </div>
      <InsightCard insight={r.insight} roleText={roleText} icon={false} />
      <p className="mh-print-note">
        {r.note ? `${r.note} ` : ""}Drawn from {r.openings_label} active ministry job openings; {typeLabel} roles; data as of {longDay(r.as_of)}.
        A guide for planning, not a guarantee of what any candidate will accept.
      </p>
      <div className="mh-print-foot">
        <img className="mh-logo" src="/ministryhub-logo-white.png" alt="" />
        <div><p>Hiring soon? Let's talk through your search.</p><strong>{BOOK_URL.replace("https://", "")}</strong></div>
      </div>
    </div>
  );
}
