import React from "react";

// A state in a word and a colour (never colour alone): ok = running fine, attention = waiting on a person, off = not set up.
const MARKS = {
  ok: ["Running", "text-[#247b50]"],
  attention: ["Needs you", "text-destructive"],
  off: ["Not set up", "text-muted-foreground"],
};

export default function StatusMark({ state, label }) {
  const [text, color] = MARKS[state];
  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap text-sm font-semibold ${color}`}>
      <span aria-hidden="true" className="size-2 rounded-full bg-current" />
      {label || text}
    </span>
  );
}
