import React from "react";
import { count } from "../format.js";

const NOTES = {
  json: "Job feed with stated pay",
  churches: "Excel leads · pay read from each job page",
  nonprofits: "Excel leads · pay read from each job page",
};

export default function SourceTabs({ sources, value, onChange }) {
  return (
    <nav className="sources" role="tablist" aria-label="Data source">
      {(sources || [{ key: value, label: "…" }]).map((s) => (
        <button
          type="button"
          role="tab"
          key={s.key}
          aria-selected={s.key === value}
          className="source"
          onClick={() => s.key !== value && onChange(s.key)}
        >
          <span className="source-label">{s.label}</span>
          {s.postings != null && (
            <span className="source-meta num">
              {count(s.postings)} postings · {count(s.paid)} with pay
              {s.key !== "json" && s.fetched < s.postings && <> · {count(s.fetched)} pages read</>}
              {s.expired > 0 && <> · {count(s.expired)} expired</>}
            </span>
          )}
          <span className="source-note">{NOTES[s.key]}</span>
        </button>
      ))}
    </nav>
  );
}
