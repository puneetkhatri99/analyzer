// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { nextReport, shareLinks } from "./share.js";

test("share link keeps every filter", () => {
  const { url } = shareLinks("https://x.org/report?role=Worship&state=Ohio&state=Indiana", "Worship pay in Ohio");
  assert.deepEqual(new URL(url).searchParams.getAll("state"), ["Ohio", "Indiana"]);
});

test("mailto is encoded and carries the link", () => {
  const { url, mailto } = shareLinks("https://x.org/report?role=Children's & Family", "Kids & Family pay");
  assert.ok(mailto.startsWith("mailto:?subject=Kids%20%26%20Family"));
  assert.ok(!/[ &]/.test(mailto.split("?")[1].replace("&body=", "")));
  assert.ok(decodeURIComponent(mailto.split("&body=")[1]).includes(url));
});

test("after sign-up only report pages are opened", () => {
  const next = (path) => nextReport(`?next=${encodeURIComponent(path)}`);
  assert.equal(next("/report?role=Worship&state=Ohio"), "/report?role=Worship&state=Ohio");
  assert.equal(next("https://evil.example/report?x"), null);
  assert.equal(next("//evil.example/report"), null);
  assert.equal(next("/admin"), null);
  assert.equal(nextReport(""), null);
});
