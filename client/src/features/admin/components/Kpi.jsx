import React from "react";

// One figure in a KPI strip: label, value (with an optional small suffix), and a line of context.
export default function Kpi({ label, value, sub, lead = false, suffix }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value num${lead ? " lead" : ""}`}>
        {value}
        {suffix && <span className="suffix">{suffix}</span>}
      </div>
      <div className="kpi-sub">{sub}</div>
    </div>
  );
}
