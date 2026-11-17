import assert from "node:assert/strict";
import test from "node:test";
import { readCataloguePrice } from "../../app/lib/catalogue-price.ts";

const updated = "2026-11-17T22:16:19.846Z";
const now = Date.parse(updated);
const pricing = { cardmarket: { unit: "EUR", low: 3.5, updated } };

test("uses the dated EUR market low and marks older data", () => {
  assert.deepEqual(readCataloguePrice(pricing, now), { low: 3.5, updatedAt: updated, stale: false });
  assert.equal(readCataloguePrice(pricing, now + 48 * 60 * 60 * 1000 + 1).stale, true);
});

test("withholds missing, malformed, undated and future observations", () => {
  for (const data of [null, {}, { tcgplayer: { low: 10 } }]) {
    assert.equal(readCataloguePrice(data, now), null);
  }
  for (const change of [{ unit: "USD" }, { low: "3.5" }, { low: 0 }, { low: Infinity }, { updated: null }, { updated: "invalid" }]) {
    assert.equal(readCataloguePrice({ cardmarket: { ...pricing.cardmarket, ...change } }, now), null);
  }
  assert.equal(readCataloguePrice(pricing, now - 1), null);
});
