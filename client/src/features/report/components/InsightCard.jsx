import React from "react";
import { Lightbulb } from "lucide-react";

// Placeholder until the search team writes these (brief: "What our search team is seeing").
export const insightText = (roleText) =>
  `[Two or three sentences from the MinistryHub team on ${roleText} searches right now: what candidates expect, what is slowing searches down, and one piece of practical advice.]`;

export default function InsightCard({ insight, roleText, icon = true }) {
  return (
    <section className="mh-insight" data-reveal={icon || undefined}>
      {icon && <span className="mh-bulb" aria-hidden="true"><Lightbulb className="size-[22px]" strokeWidth={2} /></span>}
      <div>
        <h2>What our search team is seeing</h2>
        <p>{insight || insightText(roleText)}</p>
      </div>
    </section>
  );
}
