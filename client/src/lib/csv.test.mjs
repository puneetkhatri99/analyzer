// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { toCsv } from "./csv.js";

test("quotes commas, quotes and line breaks; empty values stay empty", () => {
  const cols = [["Job", (r) => r.name], ["Pay", (r) => r.pay]];
  const out = toCsv([{ name: 'Pastor, "Youth"', pay: null }, { name: "a\nb", pay: 52000 }], cols);
  assert.equal(out, 'Job,Pay\r\n"Pastor, ""Youth""",\r\n"a\nb",52000');
});

test("text that Excel would run as a formula gets a leading quote; numbers do not", () => {
  const cols = [["A", (r) => r.a], ["B", (r) => r.b]];
  const out = toCsv([{ a: "=HYPERLINK(1)", b: -5 }, { a: "+1", b: "@x" }, { a: "-2,3", b: "\tx" }], cols);
  assert.equal(out, "A,B\r\n'=HYPERLINK(1),-5\r\n'+1,'@x\r\n\"'-2,3\",'\tx");
});
