// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { describe } from "./leadEvents.js";

test("every event type reads as a sentence", () => {
  assert.deepEqual(describe({ type: "signup", details: { role: "Worship/Music", location: "Ohio", shared: true, organization: "Grace" } }),
    ["Signed up to open a shared report", "Worship/Music · Ohio · Grace"]);
  assert.deepEqual(describe({ type: "report", details: { trigger: "update", shown: "Worship/Music in Ohio", size: ["Under 250"], type: "part-time", widened_to: "Midwest" } }),
    ["Updated the report", "Worship/Music in Ohio · Under 250 · part-time · widened to Midwest"]);
  assert.equal(describe({ type: "report", details: { trigger: "open" } })[0], "Opened a report");
  assert.equal(describe({ type: "report", details: {} })[0], "Viewed a report"); // rows from before triggers
  assert.equal(describe({ type: "offer", details: { amount: 52000, unit: "year", verdict: "Competitive." } })[0], "Checked an offer of $52,000 a year");
  assert.equal(describe({ type: "offer", details: { amount: 18.5, unit: "hour" } })[0], "Checked an offer of $18.50 an hour");
  assert.equal(describe({ type: "cta", details: { label: "Book a Call", url: "https://x" } })[0], "Went to MinistryHub: “Book a Call”");
  assert.deepEqual(describe({ type: "click", details: { label: "Reset filters", page: "/report" } }), ["Clicked “Reset filters”", "on the report"]);
  assert.deepEqual(describe({ type: "something_new" }), ["something_new", ""]); // an unknown type still shows
});
