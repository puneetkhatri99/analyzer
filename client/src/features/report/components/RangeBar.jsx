import React from "react";
import { rangeScale } from "../lib/pay.js";

// Lower quarter to upper quarter as a band, typical pay as a tick, and an optional marker (the visitor's offer).
export default function RangeBar({ p, marker }) {
  const at = rangeScale(p);
  return (
    <div className="mh-range">
      <span className="mh-range-typical-label" style={{ left: at(p.typical) }}>Typical</span>
      <div className="mh-range-track">
        <div className="mh-range-band" style={{ left: at(p.low), width: `calc(${at(p.high)} - ${at(p.low)})` }} />
        <div className="mh-range-tick" style={{ left: at(p.typical) }} />
        {marker != null && <div className="mh-range-marker" style={{ left: at(marker) }} title="Your offer" />}
      </div>
      <span className="mh-range-q" style={{ left: at(p.low) }}>Lower quarter</span>
      <span className="mh-range-q" style={{ left: at(p.high) }}>Upper quarter</span>
    </div>
  );
}
