import React from "react";
import { Card } from "@/components/ui/card";
import BarList from "./BarList.jsx";

function BreakdownCard({ title, rows, selected, unit, empty, children }) {
  return (
    <Card as="section" className="mh-card">
      <h2>{title}</h2>
      {rows.length ? <BarList rows={rows} selected={selected} unit={unit} /> : <p className="mh-muted">{empty}</p>}
      {children}
    </Card>
  );
}

// Typical pay compared across roles, church sizes, states and denominations.
export default function Breakdowns({ r }) {
  const f = r.filters;
  const where = r.scope !== "national" ? ` in ${r.area_name}` : "";
  return (
    <>
      <div data-reveal>
        <BreakdownCard title={`Compared with other roles${where}`} rows={r.by_role} selected={f.role} unit={r.unit}
          empty="Not enough listed pay to compare roles yet." />
      </div>
      <div data-reveal>
        <BreakdownCard title="By weekly attendance" rows={r.by_size} selected={f.size} unit={r.unit} empty="">
          {f.size.length > 0 && <p className="mh-small">Your selected sizes are highlighted.</p>}
        </BreakdownCard>
      </div>
      <div className="mh-two" data-reveal>
        <BreakdownCard title="Pay by state" rows={r.by_state} selected={f.state} unit={r.unit} empty="Not enough listed pay by state yet." />
        <BreakdownCard title="By denomination" rows={r.by_denomination} selected={f.denomination} unit={r.unit}
          empty="Not enough listed pay by denomination yet." />
      </div>
    </>
  );
}
