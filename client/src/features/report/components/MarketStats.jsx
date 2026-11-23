import React from "react";
import { Card } from "@/components/ui/card";
import { pay } from "../lib/pay.js";

function Stat({ title, value, children }) {
  return (
    <Card className="mh-card mh-stat">
      <h3>{title}</h3>
      {value != null && <strong>{value}</strong>}
      <p>{children}</p>
    </Card>
  );
}

// Area vs national, and this role's share of openings. `compact` shortens labels for the print view.
export default function MarketStats({ r, roleText, compact }) {
  const v = r.vs_national;
  const share = r.share_percent;
  return (
    <div className="mh-stats" data-reveal>
      {v ? (
        <Stat title={compact ? `${v.area} vs. national, all roles` : `All ministry roles: ${v.area} vs. national`}
          value={v.percent === 0 ? "On par" : `${Math.abs(v.percent)}% ${v.percent < 0 ? "lower" : "higher"}`}>
          {pay(v.area_typical, r.unit)} in {v.area}, {pay(v.national_typical, r.unit)} nationwide
        </Stat>
      ) : !compact && (  // on paper there is nobody to "pick a state", so the printed report leaves the empty box out
        <Stat title="Compared with national">
          {r.filters.state.length
            ? `${r.title.area} is combined with nationwide figures here, so there is no separate comparison.`
            : "Pick a state to compare it with national pay."}
        </Stat>
      )}
      {(share != null || !compact) && (
        <Stat title="Share of openings" value={share != null ? `${share < 1 ? "<1" : share}%` : "—"}>
          {share != null ? `of current ministry openings are ${roleText} roles` : "Pick a role to see its share."}
        </Stat>
      )}
    </div>
  );
}
