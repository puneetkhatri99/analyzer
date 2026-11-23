import React from "react";
import { Card } from "@/components/ui/card";
import { BOOK_URL } from "@/features/site/links.js";
import { longDay } from "@/lib/format.js";
import BarList, { withPay } from "./BarList.jsx";
import MarketStats from "./MarketStats.jsx";
import PayCard from "./PayCard.jsx";

// The branded export (brief P8): shown only when printing, so "Download report" saves it as a PDF.
export default function PrintReport({ r, roleText, typeLabel }) {
  const combined = [r.by_role, r.by_size, r.by_state, r.by_denomination].some((rows) => rows?.some((x) => x.merged?.length));
  return (
    <div className="mh-print" aria-hidden="true">
      <section className="mh-print-page">
        <div className="mh-print-head">
          <img className="mh-logo" src="/ministryhub-logo.png" alt="" />
          <div><p className="mh-eyebrow">Market Analysis Report</p><p>{longDay(new Date().toISOString())}</p></div>{/* taste-skill-ignore: label in the client's approved design */}
        </div>
        <h1>{r.covers.role} pay in <span className="mh-underline">{r.covers.area}</span></h1>
        {r.merged?.length > 0 && r.pay && (
          <div className="mh-print-merged">
            <p><strong>Combined data.</strong> Too few openings list pay for your exact search, so this report combines:</p>
            <ul>{r.merged.map((m) => <li key={m.kind}><strong>{m.label}:</strong> {m.chosen} → {m.shown}</li>)}</ul>
          </div>
        )}
        <PayCard r={r} typeLabel={typeLabel} />
        <MarketStats r={r} roleText={roleText} compact />
      </section>
      <section className="mh-print-page">
        <div className="mh-print-head">
          <img className="mh-logo" src="/ministryhub-logo.png" alt="" />
          <p className="mh-eyebrow">Market Analysis Report</p>
        </div>
        <div className="mh-print-cols">
          <Card className="mh-card"><h2>Compared with other roles</h2><BarList rows={r.by_role} selected={r.filters.role} unit={r.unit} /></Card>
          {withPay(r.by_size).length > 0 && <Card className="mh-card"><h2>By church size</h2><BarList rows={r.by_size} selected={r.filters.size} unit={r.unit} /></Card>}
        </div>
        <p className="mh-print-note">
          {r.note && !r.merged?.length ? `${r.note} ` : ""}{combined ? "Rows marked “combined” group similar items that each had too few pay figures to show on their own. " : ""}Drawn from {r.openings_label} active ministry job openings; {typeLabel} roles; data as of {longDay(r.as_of)}.
          A guide for planning, not a guarantee of what any candidate will accept.
        </p>
        <div className="mh-print-foot">
          <img className="mh-logo" src="/ministryhub-logo-white.png" alt="" />
          <div><p>Hiring soon? Let's talk through your search.</p><strong>{BOOK_URL.replace("https://", "")}</strong></div>
        </div>
      </section>
    </div>
  );
}
