import React from "react";
import { Card } from "@/components/ui/card";
import { count, longDate } from "@/lib/format.js";
import Kpi from "../components/Kpi.jsx";
import { usd } from "./costFormat.js";

export default function CostKpis({ totals: t }) {
  const searches = Number(t.web_searches);
  return (
    <Card className="kpis cost-kpis">
      <Kpi lead label="Spent this month" value={usd(t.this_month)} sub={`Today ${usd(t.today)}`} />
      <Kpi label="Spent in total" value={usd(t.total)} sub={t.since ? `Since ${longDate(t.since)}` : "Nothing yet"} />
      <Kpi label="Times the AI was used" value={count(t.calls)} sub={`Including ${count(searches)} web search${searches === 1 ? "" : "es"}`} />
    </Card>
  );
}
