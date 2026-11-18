import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (["./product-variant", "./cardmarket-window"].includes(specifier) && context.parentURL?.endsWith("/market-data.ts")) {
      return nextResolve(specifier + ".ts", context);
    }
    return nextResolve(specifier, context);
  },
});
const { readPriceChange } = await import("../../app/lib/market-data.ts");
const { readCardmarketWindow } = await import("../../app/lib/cardmarket-window.ts");
hooks.deregister();

test("Cardmarket overlapping windows require dated positive EUR values", () => {
  const now = Date.parse("2026-11-18T16:00:00Z");
  const valid = { avg7: 90, avg30: 100, unit: "EUR", updated: "2026-11-17T09:00:00Z" };
  assert.deepEqual(readCardmarketWindow(valid, now), {
    avg7: 90, avg30: 100, updated: valid.updated, stale: false, percent: -10,
  });
  assert.equal(readCardmarketWindow({ ...valid, avg30: 0 }, now), null);
  assert.equal(readCardmarketWindow({ ...valid, unit: "USD" }, now), null);
  assert.equal(readCardmarketWindow({ ...valid, updated: "2026-11-20" }, now), null);
  assert.equal(readCardmarketWindow({ ...valid, updated: "2026-11-15" }, now).stale, true);
});

const observation = {
  id: "tcgdex_base1-4", product_id: "pokemon_card_base1-4", status: "OK",
  url: "https://api.tcgdex.net/v2/fr/cards/base1-4", body_sha256: "a".repeat(64),
  observed_at: "2026-11-18T23:00:00Z", price_kind: "AGGREGATED_INDICATIVE_LOW", price: "99",
};
const event = {
  kind: "INDICATIVE_PRICE_CHANGE", field: "price", observation_id: observation.id,
  product_id: observation.product_id, source_url: observation.url,
  evidence_sha256: observation.body_sha256, previous_evidence_sha256: "b".repeat(64),
  window_start: "2026-11-18T22:00:00Z", window_end: observation.observed_at, before: "90", after: "99",
};

test("computes a sourced movement only from the matching observation", () => {
  assert.deepEqual(readPriceChange([event], observation), {
    before: 90, after: 99, percent: 0.1, from: event.window_start,
    to: observation.observed_at, source: observation.url,
  });
});

test("ignores mismatched, stale, or unsuccessful inputs", () => {
  for (const conflict of [{ after: "100" }, { product_id: "pokemon_card_other" }, { evidence_sha256: "c".repeat(64) },
    { source_url: "https://example.com" }, { window_start: "invalid" }, { before: "0" }]) {
    assert.equal(readPriceChange([{ ...event, ...conflict }], observation), undefined);
  }
  assert.equal(readPriceChange([event], { ...observation, status: "FAILED" }), undefined);
});
