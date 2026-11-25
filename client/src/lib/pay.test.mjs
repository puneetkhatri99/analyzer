// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { offerVerdict, parseAmount, rangeScale } from "./pay.js";

const p = { low: 40000, typical: 50000, high: 60000 };

test("offer verdict covers every band, edges included", () => {
  assert.equal(offerVerdict(39999, p, "year")[0], "Below market.");
  assert.equal(offerVerdict(40000, p, "year")[0], "Within range.");
  assert.equal(offerVerdict(50000, p, "year")[0], "Competitive.");
  assert.equal(offerVerdict(60000, p, "year")[0], "Competitive.");
  assert.equal(offerVerdict(60001, p, "year")[0], "Above market.");
});

test("amounts are read the way people type them", () => {
  assert.equal(parseAmount("$52,000"), 52000);
  assert.equal(parseAmount("18.50"), 18.5);
  assert.equal(parseAmount("abc"), null);
  assert.equal(parseAmount("0"), null);
});

test("range bar positions stay inside 0–100%", () => {
  const at = rangeScale(p);
  assert.equal(at(0), "0%");
  assert.equal(at(1e9), "100%");
  assert.ok(parseFloat(at(p.low)) < parseFloat(at(p.typical)));
});
