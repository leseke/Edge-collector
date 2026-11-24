import { makeCorpus } from "../app/lib/tcg-corpus.ts";
import assert from "node:assert/strict";
const card = {
  productId: "pokemon_card_test", name: "TEST CARD — synthetic fixture",
  observedAt: "2025-01-01T12:00:00Z", snapshotId: "20250101-1234",
  source: "TEST FIXTURE", reportSha256: "a".repeat(64), rawSha256: "b".repeat(64),
  currency: "EUR", priceKind: "aggregated", low: 12.5,
};
assert.throws(() => makeCorpus({...card, observedAt: "invalid"}));
assert.throws(() => makeCorpus({...card, observedAt: "2999-01-01T00:00:00Z"}));
console.log(JSON.stringify([makeCorpus(card), makeCorpus({...card, low: null})]));
