import React from "react";
import { MIN_PAID, count, money, moneyShort } from "../format.js";

// Capped so one thin, wide band can't squash every other row; bands past the cap are clipped.
const SCALE_CAP = 160000;

function scaleFor(rows, compact) {
  const top = Math.min(SCALE_CAP, Math.max(40000, ...rows.map((r) => r.p75 || 0)));
  const max = Math.ceil(top / 40000) * 40000;
  const step = compact ? max / 2 : max > 80000 ? 40000 : 20000;
  const ticks = [];
  for (let v = 0; v <= max; v += step) ticks.push(v);
  return { max, ticks };
}

const pct = (v, max) => `${Math.min(100, (v / max) * 100)}%`;

export default function PayLadder({ rows, nameHeader, selected, onSelect, compact = false }) {
  const benchmarked = rows.filter((r) => r.paid >= MIN_PAID);
  const thin = rows.filter((r) => r.paid < MIN_PAID);
  const { max, ticks } = scaleFor(benchmarked, compact);

  const toggle = (name) => onSelect(selected === name ? "" : name);

  return (
    <div className={`ladder${compact ? " compact" : ""}`}>
      <div className="ladder-head" aria-hidden="true">
        <span>{nameHeader}</span>
        <span className="r">{compact ? "Paid" : "With pay"}</span>
        <div className="axis num">
          {ticks.map((t) => (
            <span key={t} style={{ left: pct(t, max) }}>{moneyShort(t)}</span>
          ))}
        </div>
        <span className="r">Median</span>
      </div>

      {benchmarked.length === 0 && <p className="empty-line">No group here has {MIN_PAID} or more postings that list pay.</p>}

      {benchmarked.map((r) => (
        <button
          type="button"
          key={r.name}
          className="ladder-row"
          aria-pressed={selected === r.name}
          aria-label={`${r.name}: median ${money(r.median)} a year, middle half ${money(r.p25)} to ${money(r.p75)}, from ${r.paid} postings with listed pay`}
          title={`${r.name}\nMiddle half: ${money(r.p25)}–${money(r.p75)}\nMedian: ${money(r.median)} · ${r.paid} of ${r.postings} postings list pay`}
          onClick={() => toggle(r.name)}
        >
          <span className="ladder-name">{r.name}</span>
          <span className="r num muted ladder-n">{count(r.paid)}<span className="n-unit"> paid</span></span>
          <span className="track" aria-hidden="true">
            {ticks.slice(1, -1).map((t) => <span key={t} className="gridline" style={{ left: pct(t, max) }} />)}
            <span className="band" style={{ left: pct(r.p25, max), width: `calc(${pct(r.p75, max)} - ${pct(r.p25, max)})` }} />
            <span className="tick" style={{ left: pct(r.median, max) }} />
          </span>
          <span className="r num ladder-median">{money(r.median)}</span>
        </button>
      ))}

      {thin.length > 0 && benchmarked.length > 0 && <div className="ladder-divider" />}
      {thin.map((r) => (
        <button
          type="button"
          key={r.name}
          className="ladder-row thin"
          aria-pressed={selected === r.name}
          aria-label={`${r.name}: only ${r.paid} of ${r.postings} postings list pay, too few to benchmark`}
          onClick={() => toggle(r.name)}
        >
          <span className="ladder-name">{r.name}</span>
          <span className="r num muted ladder-n">{count(r.paid)}<span className="n-unit"> paid</span></span>
          <span className="track"><span className="thin-note">{r.paid === 0 ? "No pay listed" : `Too few to benchmark`}</span></span>
          <span className="r num ladder-median">—</span>
        </button>
      ))}
    </div>
  );
}
