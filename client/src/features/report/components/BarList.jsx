import React from "react";
import { pay } from "../lib/pay.js";

// Typical pay per group as horizontal bars; the visitor's picks are highlighted. Groups without data show a placeholder.
export default function BarList({ rows, selected = [], unit, placeholder = "[$XX,XXX]" }) {
  const max = Math.max(...rows.map((r) => r.typical || 0), 1);
  return (
    <div className="mh-bars">
      {rows.map((r) => {
        const empty = r.typical == null;
        return (
          <div key={r.name} className={`mh-bar-row${selected.includes(r.name) ? " is-on" : ""}`}>
            <span className="mh-bar-name">{r.name}</span>
            <span className="mh-bar-track">
              <span className={`mh-bar${empty ? " is-empty" : ""}`} style={{ width: empty ? "40%" : `${(r.typical / max) * 100}%` }} />
            </span>
            <span className="mh-bar-value">{empty ? placeholder : pay(r.typical, unit)}</span>
          </div>
        );
      })}
    </div>
  );
}
