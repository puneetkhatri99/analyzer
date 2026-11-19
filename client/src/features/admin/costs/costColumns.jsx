import { count, longDate, when } from "@/lib/format.js";
import { purpose, runName, usd } from "./costFormat.js";

const num = { right: true, className: "num" };

export const BY_PURPOSE = [
  { header: "What the AI did", cell: (p) => purpose(p.purpose) },
  { header: "Times", cell: (p) => count(p.calls), ...num },
  { header: "Average each", cell: (p) => usd(p.avg_cost), ...num },
  { header: "Total", cell: (p) => usd(p.cost), ...num },
];

export const BY_RUN = [
  { header: "What ran", cell: (r) => runName(r.run_id) },
  { header: "When", cell: (r) => when(r.started) },
  { header: "AI requests", cell: (r) => count(r.calls), ...num },
  { header: "Web searches", cell: (r) => count(r.web_searches), ...num },
  { header: "Cost", cell: (r) => usd(r.cost), ...num },
];

export const BY_DAY = [
  { header: "Day", cell: (d) => longDate(d.day) },
  { header: "Times", cell: (d) => count(d.calls), ...num },
  { header: "Cost", cell: (d) => usd(d.cost), ...num },
];
