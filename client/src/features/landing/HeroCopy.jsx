import React from "react";
import { longDay } from "@/lib/format.js";

function Check() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="13" fill="var(--mh-teal)" />
      <path d="M8 13.5l3.2 3.2L18 10" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const POINTS = [
  "Current openings, not last year's survey",
  "Compare by state, church size and denomination",
  "A ready-made report to share with your board or elders",
];

export default function HeroCopy({ landing }) {
  return (
    <div className="mh-hero-copy" data-reveal>
      <p className="mh-eyebrow">MinistryHub Market Analysis Tool · Free</p>{/* taste-skill-ignore: label in the client's approved design */}
      <h1>What are churches paying for this role <span className="mh-underline">right now?</span></h1>
      <p className="mh-lede">
        Live pay benchmarks drawn from {landing?.openings_label || "thousands of"} active ministry job openings across the United States.
        Pick a role and a location and get your report in under a minute.
      </p>
      <ul className="mh-checks">
        {POINTS.map((p) => <li key={p}><Check />{p}</li>)}
      </ul>
      <p className="mh-small">Built by the MinistryHub search team. Data as of {longDay(landing?.as_of)}.</p>
    </div>
  );
}
