import React from "react";

const ICONS = {
  chart: <path d="M7 17V11M11 17V7M15 17v-4M19 17V9" />,
  filter: <path d="M5 8h14M8 12h8M10.5 16h3" />,
  doc: <><path d="M8 4h6l4 4v12H8z" /><path d="M11 12h4M11 15h4" /></>,
};

const FEATURES = [
  ["chart", "The pay range for your role", "Typical pay and the range most churches offer, for your role in your area."],
  ["filter", "How you compare", "Adjust by state, church size and denomination. Check an offer you're planning against the market."],
  ["doc", "A report you can share", "Download a prepared report for your board, elders or personnel committee."],
];

export default function ReportFeatures() {
  return (
    <section className="mh-wrap mh-section" data-reveal>
      <h2 className="mh-h2">What's in your report</h2>
      <p className="mh-sub">A clear answer first, then the detail if you want it.</p>
      <div className="mh-features">
        {FEATURES.map(([icon, title, text]) => (
          <div className="mh-feature" key={title}>
            <span className="mh-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[icon]}</svg>
            </span>
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
