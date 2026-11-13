import React from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, XAxis, YAxis } from "recharts";
import { money, moneyShort } from "@/lib/format.js";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

const CONFIG = { count: { label: "Postings", color: "var(--chart-1)" } };

// A histogram of annual pay. The x axis is in dollars, so the median line sits at its exact value inside its band.
export default function PayDistribution({ histogram, bin, cap, median }) {
  const data = histogram.map((b) => ({ from: b.from, mid: b.from + bin / 2, count: b.count }));
  const end = histogram.length ? histogram[histogram.length - 1].from + bin : bin;
  const band = (from) => (from >= cap ? `${money(cap)} or more` : `${money(from)}–${money(from + bin - 1)}`);
  const tick = (v) => (v >= cap ? `${moneyShort(cap)}+` : moneyShort(v));
  // the label sits right of the line, or left of it near the right edge
  const labelSide = median > end * 0.7 ? "insideTopRight" : "insideTopLeft";

  return (
    <div className="chart-box" role="img" aria-label={`Histogram of annual pay in $${bin / 1000}k bands; median ${money(median)}.`}>
      <ChartContainer config={CONFIG} className="absolute inset-0 aspect-auto">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -8 }} barCategoryGap={1}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="mid" type="number" domain={[0, end]} ticks={histogram.map((b) => b.from)} tickFormatter={tick}
            interval="preserveEnd" minTickGap={14} tickLine={false} />
          <YAxis allowDecimals={false} tickCount={5} axisLine={false} tickLine={false} width={44} />
          <ChartTooltip cursor={{ fill: "var(--muted)" }}
            content={<ChartTooltipContent hideIndicator labelFormatter={(_, p) => band(p[0].payload.from)}
              formatter={(v) => `${v} posting${v === 1 ? "" : "s"}`} />} />
          <Bar dataKey="count" fill="var(--color-count)" isAnimationActive={false} />
          {median != null && (
            <ReferenceLine x={median} stroke="var(--chart-2)" strokeWidth={2}
              label={{ value: `Median ${money(median)}`, position: labelSide, fill: "var(--chart-2)", fontSize: 12, fontWeight: 500 }} />
          )}
        </BarChart>
      </ChartContainer>
    </div>
  );
}
