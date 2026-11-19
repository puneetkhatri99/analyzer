import React from "react";

// One setting: what it is and why, in words, on the left; the controls on the right.
// Stacks on a phone (the words first).
export default function SettingRow({ title, description, children }) {
  return (
    <section className="grid gap-4 border-t border-border py-8 first:border-t-0 first:pt-2 md:grid-cols-[minmax(0,300px)_minmax(0,1fr)] md:items-start md:gap-10">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        <div className="mt-1.5 grid gap-2.5 text-[15px] leading-6 text-muted-foreground [&_p]:m-0">{description}</div>
      </div>
      <div className="grid min-w-0 content-start gap-5 rounded-lg border border-border bg-card p-5 [&_p]:m-0">{children}</div>
    </section>
  );
}
