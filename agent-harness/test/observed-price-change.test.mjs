import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "./product-variant" && context.parentURL?.endsWith("/market-data.ts")) {
      return nextResolve("./product-variant.ts", context);
    }
    return nextResolve(specifier, context);
  },
});
const { readPriceChange } = await import("../../app/lib/market-data.ts");
hooks.deregister();

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
