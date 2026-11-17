import test from "node:test";
import assert from "node:assert/strict";
import { createDeepSeekAdapter } from "../deepseek-adapter.mjs";
import { analyzePriceChanges, preparePriceAnalysis } from "../market-price-analysis.mjs";

const event = {
  id: "a".repeat(64), kind: "INDICATIVE_PRICE_CHANGE", field: "price",
  product_id: "pokemon_card_base1-4", before: "90", after: "99",
  window_start: "2026-11-17T22:00:00Z", window_end: "2026-11-17T23:00:00Z",
  source_url: "https://api.tcgdex.net/v2/fr/cards/base1-4",
  previous_evidence_sha256: "b".repeat(64), evidence_sha256: "c".repeat(64),
};
const report = (...events) => ({ schema: "edge.commercial.events.v1", events });

test("dry run keeps only distinct, sourced and significant observations", async () => {
  const result = await analyzePriceChanges(report(event, event, { ...event, id: "d".repeat(64), after: "92" },
    { ...event, id: "e".repeat(64), source_url: "http://example.com" }));
  assert.equal(result.status, "DRY_RUN");
  assert.equal(result.candidates.length, 1);
  assert.equal(result.candidates[0].changePercent, 10);
  assert.deepEqual(result.analyses, []);
  assert.equal(preparePriceAnalysis(report(event), { thresholdPercent: 11 }).length, 0);
});

test("the DeepSeek adapter sends only the requested analysis brief through injected transport", async () => {
  const generate = createDeepSeekAdapter({
    enabled: true, apiKey: "fixture", task: "ANALYZE_MARKET_PRICE_CHANGE",
    fetchImpl: async (_url, payload) => {
      const brief = JSON.parse(JSON.parse(payload.body).messages[1].content);
      assert.equal(brief.evidence.after, "99");
      assert.equal(brief.purchaseAuthorized, false);
      return new Response(JSON.stringify({ choices: [{ message: { content: JSON.stringify({
        eventId: brief.evidence.eventId, commentary: "Variation observée, cause à vérifier.",
      }) } }] }));
    },
  });
  const result = await analyzePriceChanges(report(event), { generate });
  assert.equal(result.analyses[0].status, "UNREVIEWED");
  assert.equal(result.candidates[0].after, "99");
});

test("invalid model output cannot substitute a price", async () => {
  const result = await analyzePriceChanges(report(event), {
    generate: async () => JSON.stringify({ eventId: event.id, commentary: "Test", after: "123" }),
  });
  assert.equal(result.analyses[0].status, "ANALYSIS_UNAVAILABLE");
  assert.equal(result.candidates[0].after, "99");
});
