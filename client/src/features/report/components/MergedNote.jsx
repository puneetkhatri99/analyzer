import React from "react";
import { ArrowRight, Layers } from "lucide-react";

// Says plainly what was combined because too few openings list pay: one row per filter, "what you chose -> what the
// figures cover". The server sends the rows (merged: kind, label, chosen, shown).
export default function MergedNote({ merged }) {
  return (
    <section className="mh-merged" aria-labelledby="mh-merged-title">
      <div className="mh-merged-head">
        <Layers className="size-5" aria-hidden="true" />
        <div>
          <h2 id="mh-merged-title">We widened your search</h2>
          <p>Too few openings list pay for this exact search, so we combined similar data to give you a reliable range.</p>
        </div>
      </div>
      <dl className="mh-merged-list">
        {merged.map((m) => (
          <div className="mh-merged-row" key={m.kind}>
            <dt>{m.label}</dt>
            <dd>
              <span className="mh-merged-from">{m.chosen}</span>
              <ArrowRight className="mh-merged-arrow" role="img" aria-label="widened to" />
              <strong className="mh-merged-to">{m.shown}</strong>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
