import React from "react";
import { Card } from "@/components/ui/card";
import { count, longDate } from "@/lib/format.js";
import Kpi from "../components/Kpi.jsx";
import { usd } from "./costFormat.js";

export default function CostKpis({ totals: t }) {
  const searches = Number(t.web_searches);
  return (
    <Card className="kpis cost-kpis">
      <Kpi lead label="Total AI spend" value={usd(t.total)} sub={t.since ? `Since ${longDate(t.since)}` : "No AI calls yet"} />
      <Kpi label="This month" value={usd(t.this_month)} sub={`Today ${usd(t.today)}`} />
      <Kpi label="AI calls" value={count(t.calls)} sub={`${count(searches)} web search${searches === 1 ? "" : "es"}`} />
      <Kpi label="Tokens" value={count(Number(t.input_tokens) + Number(t.output_tokens))}
        sub={`${count(t.input_tokens)} in · ${count(t.output_tokens)} out`} />
    </Card>
  );
}
