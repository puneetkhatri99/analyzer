import React, { useState } from "react";
import { MIN_PAID, count, money } from "../format.js";

export default function BreakdownList({ rows, nameHeader, selected, onSelect, limit }) {
  const [showAll, setShowAll] = useState(false);
  const visible = limit && !showAll ? rows.slice(0, limit) : rows;
  const most = Math.max(1, ...rows.map((r) => r.postings));

  if (rows.length === 0) return <p className="empty-line">None of the matching postings state this.</p>;

  return (
    <div>
      <div className="list-head" aria-hidden="true">
        <span>{nameHeader}</span>
        <span className="r">Postings</span>
        <span className="r">Median pay</span>
      </div>
      {visible.map((r) => {
        const benchmarked = r.paid >= MIN_PAID;
        const body = (
          <>
            <span style={{ minWidth: 0 }}>
              <span className="list-name" style={{ display: "block" }}>{r.name}</span>
              <span className="list-bar" aria-hidden="true"><span style={{ width: `${(r.postings / most) * 100}%` }} /></span>
            </span>
            <span className="r num">{count(r.postings)}</span>
            <span
              className={`r num median${benchmarked ? "" : " none"}`}
              title={benchmarked ? `${r.paid} postings list pay` : `Only ${r.paid} list pay`}
            >
              {benchmarked ? money(r.median) : "—"}
            </span>
          </>
        );
        return onSelect ? (
          <button
            type="button"
            key={r.name}
            className="list-row"
            aria-pressed={selected === r.name}
            onClick={() => onSelect(selected === r.name ? "" : r.name)}
          >
            {body}
          </button>
        ) : (
          <div key={r.name} className="list-row">{body}</div>
        );
      })}
      {limit && rows.length > limit && (
        <div className="card-foot">
          <button type="button" className="link-btn" onClick={() => setShowAll((v) => !v)}>
            {showAll ? "Show fewer" : `Show all ${rows.length}`}
          </button>
        </div>
      )}
    </div>
  );
}
