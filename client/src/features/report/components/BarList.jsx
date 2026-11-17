import React from "react";
import { pay } from "../lib/pay.js";

// Groups with enough pay to show (the API sends church sizes without data as typical: null).
export const withPay = (rows) => rows.filter((r) => r.typical != null);

// Typical pay per group as horizontal bars; the visitor's picks are highlighted.
export default function BarList({ rows, selected = [], unit }) {
  const shown = withPay(rows);
  const max = Math.max(...shown.map((r) => r.typical), 1);
  return (
    <div className="mh-bars">
      {shown.map((r) => (
        <div key={r.name} className={`mh-bar-row${selected.includes(r.name) ? " is-on" : ""}`}>
          {/* a break after "/" so "Administrative/Operations" wraps between words, not mid-word */}
          <span className="mh-bar-name">{r.name.replaceAll("/", "/\u200b")}</span>
          <span className="mh-bar-track"><span className="mh-bar" style={{ width: `${(r.typical / max) * 100}%` }} /></span>
          <span className="mh-bar-value">{pay(r.typical, unit)}</span>
        </div>
      ))}
    </div>
  );
}
