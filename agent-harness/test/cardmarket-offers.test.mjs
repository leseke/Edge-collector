import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";

const hook = registerHooks({
  resolve(name, context, next) {
    return next(name === "./listing-analysis" ? "./listing-analysis.ts" : name, context);
  },
});
const { cardmarketOfferStorageKey, observedCardmarketOffer, readCardmarketOffers } =
  await import("../../app/lib/cardmarket-offers.ts");
hook.deregister();

const page = "https://www.cardmarket.com/fr/Pokemon/Products/Singles/Evolving-Skies/Umbreon-VMAX-V3";
const date = "2026-11-18T16:00:00.000Z";
test("offers keep clean Cardmarket provenance, exact euro cents and condition", () => {
  const item = observedCardmarketOffer(page + "?language=2#offers", "160,25", "NM", date);
  assert.deepEqual(item, { source: page, cents: 16025, condition: "NM", observedAt: date });
  const read = readCardmarketOffers(JSON.stringify([item, { ...item, source: "https://example.com" }]));
  assert.deepEqual(read, [item]);
  assert.equal(observedCardmarketOffer(page, "0", "NM", date), null);
  assert.equal(observedCardmarketOffer(page, "10", "UNKNOWN", date), null);
  assert.equal(observedCardmarketOffer(page.replace("www.cardmarket.com", "cardmarket.com.example.com"), "10", "NM", date), null);
});

test("the same catalogue card has distinct local histories for French and Italian", () => {
  assert.notEqual(cardmarketOfferStorageKey("swsh7-215", "fr"), cardmarketOfferStorageKey("swsh7-215", "it"));
  assert.deepEqual(readCardmarketOffers("invalid"), []);
  const item = observedCardmarketOffer(page, "15", "EX", date);
  assert.equal(readCardmarketOffers(JSON.stringify(Array(25).fill(item))).length, 20);
});
