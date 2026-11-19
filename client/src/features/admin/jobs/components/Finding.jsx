import React from "react";
import { MIN_PAID, count, money } from "@/lib/format.js";
import { isSet } from "../lib/filters.js";

// One sentence that states the answer for the current filters, in plain words.
export default function Finding({ filters, stats }) {
  const subject = filters.role || "all roles";
  const where = filters.region ? ` in ${filters.region}` : "";
  const others = Object.entries(filters).some(([k, v]) => !["role", "region"].includes(k) && isSet(v));
  const scope = `${subject}${where}${others ? " matching your filters" : ""}`;
  const unpaid = stats.postings - stats.paid;

  if (stats.postings === 0) return <>No postings match these filters.</>;
  if (stats.paid < MIN_PAID) {
    return <>Only {count(stats.paid)} of {count(stats.postings)} postings for {scope} list pay, too few to benchmark. Widen the filters to compare.</>;
  }
  return (
    <>
      Median listed pay for {scope} is <strong>{money(stats.median)} a year</strong>, from {count(stats.paid)} postings that state it.
      {unpaid > 0 && <> {count(unpaid)} of {count(stats.postings)} postings list no pay at all.</>}
      {/* the public report counts hourly pay only for part-time figures, so its medians differ from these */}
      <span className="muted small block mt-1">
        Hourly pay counts here as a year at 2,080 hours. The public report leaves part-time and hourly jobs out of its
        full-time figures, so its medians can differ.
      </span>
    </>
  );
}
