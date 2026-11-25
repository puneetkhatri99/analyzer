import React from "react";
import { pay } from "@/lib/pay.js";

// Groups with enough pay to show (the API sends church sizes without data as typical: null).
export const withPay = (rows) => rows.filter((r) => r.typical != null);

// Typical pay per group as horizontal bars; the visitor's picks are highlighted. A row that combines several groups
// (the API sends them as `merged`) says which, and lights up when any of them was picked.
// Few combined groups are named; many are counted, with the full list for screen readers.
const combinedNote = (m) => (m.length <= 3 ? `Combined: ${m.join(", ")}` : `${m.length} combined`);

export default function BarList({ rows, selected = [], unit }) {
  const shown = withPay(rows);
  const max = Math.max(...shown.map((r) => r.typical), 1);
  return (
    <div className="mh-bars">
      {shown.map((r) => (
        <div key={r.name} className={`mh-bar-row${[r.name, ...(r.merged || [])].some((n) => selected.includes(n)) ? " is-on" : ""}`}>
          {/* a break after "/" so "Administrative/Operations" wraps between words, not mid-word */}
          <span className="mh-bar-name">
            {r.name.replaceAll("/", "/\u200b")}
            {r.merged?.length > 0 && (
              <small className="mh-bar-merged" title={r.merged.join(", ")}>
                {combinedNote(r.merged)}
                {r.merged.length > 3 && <span className="sr-only">: {r.merged.join(", ")}</span>}
              </small>
            )}
          </span>
          <span className="mh-bar-track"><span className="mh-bar" style={{ width: `${(r.typical / max) * 100}%` }} /></span>
          <span className="mh-bar-value">{pay(r.typical, unit)}</span>
        </div>
      ))}
      {shown.some((r) => r.merged?.length > 0) && (
        <p className="mh-small mh-bars-legend">Rows marked “combined” group similar items that each had too few pay figures to show on their own.</p>
      )}
    </div>
  );
}
