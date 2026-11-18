// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { EMPTY_FILTERS, filtersFromUrl, sourceFromUrl, toggleSource } from "./filters.js";

test("filters keep their types and ignore unknown keys", () => {
  const f = filtersFromUrl("?role=Missions&min_salary=50000&has_pay=true&bogus=1");
  assert.equal(f.role, "Missions");
  assert.equal(f.min_salary, 50000);
  assert.equal(f.has_pay, true);
  assert.equal("bogus" in f, false);
  assert.equal(f.region, EMPTY_FILTERS.region);
});

test("bad numbers fall back to empty; unknown sources to the feed", () => {
  assert.equal(filtersFromUrl("?min_church_size=lots").min_church_size, 0);
  assert.deepEqual(sourceFromUrl("?source=elsewhere"), ["json"]);
  assert.deepEqual(sourceFromUrl("?source=churches"), ["churches"]);
  assert.deepEqual(sourceFromUrl("?source=nonprofits,bogus,json"), ["json", "nonprofits"]);
});

test("sources toggle on and off, but the last one stays", () => {
  assert.deepEqual(toggleSource(["json"], "nonprofits"), ["json", "nonprofits"]);
  assert.deepEqual(toggleSource(["json", "nonprofits"], "json"), ["nonprofits"]);
  assert.deepEqual(toggleSource(["churches"], "churches"), ["churches"]);
});
