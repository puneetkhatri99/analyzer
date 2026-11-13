// node --test src/csv.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { toCsv } from "./csv.js";

test("quotes commas, quotes and line breaks; empty values stay empty", () => {
  const cols = [["Job", (r) => r.name], ["Pay", (r) => r.pay]];
  const out = toCsv([{ name: 'Pastor, "Youth"', pay: null }, { name: "a\nb", pay: 52000 }], cols);
  assert.equal(out, 'Job,Pay\r\n"Pastor, ""Youth""",\r\n"a\nb",52000');
});
