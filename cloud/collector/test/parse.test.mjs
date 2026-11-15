import { test } from "node:test";
import assert from "node:assert/strict";
import { parseIndicativePrice } from "../src/parse.mjs";

test("parses real-shape indicative price without claiming sale", () => {
  assert.deepEqual(parseIndicativePrice(JSON.stringify({ pricing: { cardmarket: { low: 1.29, updated: "2026-11-15" } } })),
    { price: 129, updated: "2026-11-15" });
});
test("rejects absent or malformed source data rather than storing a successful empty observation", () => {
  for (const value of ["{}", '{"pricing":{}}', '{"pricing":{"cardmarket":{"low":null}}}', '{"pricing":{"cardmarket":{"low":"1.29"}}}', '{"pricing":{"cardmarket":{"low":-1}}}', "null", "[]", "{bad"]) {
    assert.throws(() => parseIndicativePrice(value));
  }
});
test("rejects nonfinite and unreasonably large amounts", () => {
  assert.throws(() => parseIndicativePrice('{"pricing":{"cardmarket":{"low":1000001}}}'));
});
