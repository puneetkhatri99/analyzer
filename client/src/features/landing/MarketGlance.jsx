import React from "react";
import { money, moneyShort } from "@/lib/format.js";

// "At a glance" figures. Days open and attendance aren't collected yet, so they show the design's placeholders.
export default function MarketGlance({ landing: l }) {
  const stats = [
    [l?.typical ? money(l.typical) : "…", "Median pay across all ministry roles nationwide"],
    [l?.low ? `${moneyShort(l.low)}–${moneyShort(l.high)}` : "…", "What the middle half of ministry roles pay"],
    [l?.avg_attendance ?? "[XXX]", "Average weekly attendance of churches hiring"],
    [l?.days_open != null ? `${l.days_open} days` : "[XX] days", "Typical time a ministry role stays open"],
  ];
  return (
    <section className="mh-glance">
      <div className="mh-wrap">
        <p className="mh-eyebrow">The ministry job market at a glance</p>{/* taste-skill-ignore: label in the client's approved design */}
        <div className="mh-glance-grid" data-reveal>
          {stats.map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
        </div>
      </div>
    </section>
  );
}
