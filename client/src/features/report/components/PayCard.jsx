import React from "react";
import { longDay } from "@/lib/format.js";
import { pay, per } from "@/lib/pay.js";
import RangeBar from "./RangeBar.jsx";

// The answer: typical pay, the range most churches offer, and how sure we are.
export default function PayCard({ r, typeLabel }) {
  const p = r.pay;
  if (!p) {
    return (
      <section className="mh-pay">
        <h2 className="mh-pay-label">Typical pay, {typeLabel}</h2>
        <p className="mh-pay-empty">{r.note}</p>
      </section>
    );
  }
  // the title names the visitor's states; say so when the figures come from a wider area
  const widened = r.filters.state.length > 0 && r.scope !== "state";
  const from = widened ? ` · ${r.scope === "national" ? "Nationwide" : r.area_name}` : "";
  return (
    <section className="mh-pay" data-reveal>
      <div className="mh-pay-top">
        <div>
          <h2 className="mh-pay-label">Typical pay, {typeLabel}{from}</h2>
          <p className="mh-pay-big">{pay(p.typical, r.unit)}<span>{per(r.unit)}</span></p>
        </div>
        <div className="mh-pay-range">
          <span>Most churches offer</span>
          <strong>{pay(p.low, r.unit)} – {pay(p.high, r.unit)}</strong>
        </div>
      </div>
      <RangeBar p={p} unit={r.unit} />
      <div className="mh-pay-badges">
        <span className="mh-confidence"><i aria-hidden="true" />Confidence: {p.confidence}</span>
        {r.merged?.length > 0 && <span className="mh-confidence mh-confidence-merged"><i aria-hidden="true" />Based on combined data</span>}
      </div>
      <p className="mh-pay-foot">Drawn from {r.openings_label} active ministry job openings. Data as of {longDay(r.as_of)}.</p>
    </section>
  );
}
