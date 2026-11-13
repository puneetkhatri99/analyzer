import React from "react";
import { count, longDate } from "@/lib/format.js";
import { purpose, usd, when } from "./costFormat.js";

const num = { right: true, className: "num" };

export const BY_PURPOSE = [
  { header: "Purpose", cell: (p) => purpose(p.purpose) },
  { header: "Calls", cell: (p) => count(p.calls), ...num },
  { header: "Avg per call", cell: (p) => usd(p.avg_cost), ...num },
  { header: "Total", cell: (p) => usd(p.cost), ...num },
];

export const BY_DAY = [
  { header: "Day", cell: (d) => longDate(d.day) },
  { header: "Calls", cell: (d) => count(d.calls), ...num },
  { header: "Spend", cell: (d) => usd(d.cost), ...num },
];

export const RECENT = [
  { header: "When", cell: (r) => when(r.created_at) },
  { header: "Purpose", cell: (r) => purpose(r.purpose) },
  { header: "Job URL", className: "url-cell", cell: (r) => <a href={r.url} target="_blank" rel="noopener noreferrer" title={r.url}>{r.url}</a> },
  { header: "Admin", className: "muted", cell: (r) => r.admin_email },
  { header: "Tokens in / out", cell: (r) => `${count(r.input_tokens)} / ${count(r.output_tokens)}`, ...num },
  { header: "Searches", cell: (r) => r.web_searches, ...num },
  { header: "Cost", cell: (r) => (r.cost_usd == null ? "—" : usd(r.cost_usd)), ...num },
];
