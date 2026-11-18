import assert from "node:assert/strict";
import test from "node:test";
import { readCataloguePrice, readCatalogueQuote } from "../../app/lib/catalogue-price.ts";

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

test("prefers dated EUR prices and uses explicit provider and currency for fallback", () => {
  const us = { unit: "USD", updated, normal: { lowPrice: 9 }, holofoil: { lowPrice: 4 } };
  assert.equal(readCatalogueQuote({ ...pricing, tcgplayer: us }, now).currency, "EUR");
  assert.equal(readCatalogueQuote(pricing, now).marketLanguage, null);
  assert.equal(readCatalogueQuote({ cardmarket: { unit: "EUR", updated, "low-holo": 7 }, tcgplayer: us }, now).low, 7);
  assert.deepEqual(readCatalogueQuote({ tcgplayer: us }, now), {
    low: 4, updatedAt: updated, stale: false, currency: "USD", provider: "TCGplayer", marketLanguage: null, variant: "holofoil",
  });
  assert.equal(readCatalogueQuote({ tcgplayer: { ...us, updated: null } }, now), null);
});
