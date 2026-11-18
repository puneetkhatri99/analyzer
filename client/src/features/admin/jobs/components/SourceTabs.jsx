import React from "react";
import { count } from "@/lib/format.js";

const NOTES = {
  json: "Job feed with stated pay",
  churches: "Excel leads · pay read from each job page",
  nonprofits: "Excel leads · pay read from each job page",
};

// Toggle buttons: any mix of sources can be shown together; at least one stays on.
export default function SourceTabs({ sources, value, onChange }) {
  return (
    <div role="group" aria-label="Data sources (choose one or more)" className="sources">
      {(sources || value.map((key) => ({ key, label: "…" }))).map((s) => (
        <button type="button" key={s.key} aria-pressed={value.includes(s.key)} onClick={() => onChange(s.key)} className="source">
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
    </div>
  );
}
