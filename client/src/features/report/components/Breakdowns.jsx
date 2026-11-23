import React from "react";
import { Card } from "@/components/ui/card";
import BarList, { withPay } from "./BarList.jsx";

const MIN_STATES = 2; // one row compares nothing (thin states arrive combined by region)

function BreakdownCard({ title, rows, selected, unit, children }) {
  return (
    <Card as="section" className="mh-card">
      <h2>{title}</h2>
      <BarList rows={rows} selected={selected} unit={unit} />
      {children}
    </Card>
  );
}

// " in Ohio", " in the Midwest"; nothing when the figures are national.
export const areaPhrase = (r) => (r.scope === "region" ? ` in the ${r.area_name}` : r.scope === "state" || r.scope === "nearby" ? ` in ${r.area_name}` : "");

// Typical pay compared across roles, church sizes, states and denominations. Groups with too little pay arrive
// combined with similar ones (see BarList); a section with nothing to compare is left out.
export default function Breakdowns({ r }) {
  const f = r.filters;
  const sizes = withPay(r.by_size);
  const states = withPay(r.by_state).length >= MIN_STATES ? r.by_state : [];
  const denoms = withPay(r.by_denomination);
  const pair = [
    states.length > 0 && <BreakdownCard key="state" title="Pay by state" rows={states} selected={f.state} unit={r.unit} />,
    denoms.length > 0 && <BreakdownCard key="denom" title="By denomination" rows={denoms} selected={f.denomination} unit={r.unit} />,
  ].filter(Boolean);
  return (
    <>
      {withPay(r.by_role).length > 0 && (
        <div data-reveal>
          <BreakdownCard title={`Compared with other roles${areaPhrase(r)}`} rows={r.by_role} selected={f.role} unit={r.unit} />
        </div>
      )}
      {sizes.length > 0 && (
        <div data-reveal>
          <BreakdownCard title="By church size" rows={sizes} selected={f.size} unit={r.unit}>
            {f.size.length > 0 && <p className="mh-small">Your selected sizes are highlighted.</p>}
          </BreakdownCard>
        </div>
      )}
      {pair.length > 0 && <div className={pair.length === 2 ? "mh-two" : undefined} data-reveal>{pair}</div>}
    </>
  );
}
