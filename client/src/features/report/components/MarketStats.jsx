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

// Area vs national, time open, and this role's share of openings. `compact` shortens labels for the print view.
export default function MarketStats({ r, roleText, compact }) {
  const v = r.vs_national;
  const share = r.share_percent;
  return (
    <div className="mh-stats" data-reveal>
      {v ? (
        <Stat title={`${v.area} vs. national, all ${compact ? "roles" : "ministry roles"}`}
          value={v.percent === 0 ? "On par" : `${Math.abs(v.percent)}% ${v.percent < 0 ? "lower" : "higher"}`}>
          {pay(v.area_typical, r.unit)} in {v.area}, {pay(v.national_typical, r.unit)} nationwide
        </Stat>
      ) : (
        <Stat title="Compared with national">Pick a state to compare it with national pay.</Stat>
      )}
      <Stat title="Typical time open" value={r.days_open != null ? `${r.days_open} days` : "[XX] days"}>
        How long {roleText} roles stay posted
      </Stat>
      <Stat title="Share of openings" value={share != null ? `${share < 1 ? "<1" : share}%` : "—"}>
        {share != null ? `of current ministry openings are ${roleText} roles` : "Pick a role to see its share."}
      </Stat>
    </div>
  );
}
