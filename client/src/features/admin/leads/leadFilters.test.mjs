// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { NO_FILTERS, choices, filterLeads, isFiltered } from "./leadFilters.js";

const now = Date.parse("2026-11-18T12:00:00Z");
const leads = [
  { name: "Ann", email: "ann@a.org", role: "Worship/Music", location: "Ohio", created_at: "2026-11-17T10:00:00Z", hot: true, report_email: "sent" },
  { name: "Ben", email: "ben@b.org", role: "Youth", location: "Texas", created_at: "2026-10-01T10:00:00Z", booked: true, report_email: "failed" },
  { name: "Cy", email: "cy@c.org", role: "Worship/Music", location: "nationwide", created_at: "2026-11-01T10:00:00Z", report_email: "skipped" },
];
const names = (f) => filterLeads(leads, { ...NO_FILTERS, ...f }, now).map((l) => l.name);

test("each filter narrows the list, and they combine", () => {
  assert.deepEqual(names({}), ["Ann", "Ben", "Cy"]);
  assert.deepEqual(names({ role: "Worship/Music" }), ["Ann", "Cy"]);
  assert.deepEqual(names({ location: "Texas" }), ["Ben"]);
  assert.deepEqual(names({ since: "week" }), ["Ann"]);
  assert.deepEqual(names({ since: "month" }), ["Ann", "Cy"]);
  assert.deepEqual(names({ show: "booked" }), ["Ben"]);
  assert.deepEqual(names({ show: "email_failed" }), ["Ben", "Cy"]);
  assert.deepEqual(names({ role: "Worship/Music", since: "month", show: "hot" }), ["Ann"]);
  assert.deepEqual(names({ query: "  BEN " }), ["Ben"]);
});

test("filter choices and the filtered flag", () => {
  assert.deepEqual(choices(leads, "role"), ["Worship/Music", "Youth"]);
  assert.equal(isFiltered(NO_FILTERS), false);
  assert.equal(isFiltered({ ...NO_FILTERS, query: "  " }), false);
  assert.equal(isFiltered({ ...NO_FILTERS, location: "Ohio" }), true);
});
