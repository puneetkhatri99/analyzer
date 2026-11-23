import React from "react";
import { count, money, moneyShort } from "@/lib/format.js";

// "At a glance" figures. Attendance comes back null until there's enough data, and is then left out.
export default function MarketGlance({ landing: l }) {
  const stats = [
    [l?.typical ? money(l.typical) : "…", "Median pay across all ministry roles nationwide"],
    [l?.low ? `${moneyShort(l.low)}–${moneyShort(l.high)}` : "…", "What the middle half of ministry roles pay"],
    [l?.attendance && `${count(l.attendance)}+`, "Typical size of churches hiring"],
  ].filter(([value]) => value);
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
