// CI smoke: authentic D1 SELECT payload, deterministic stand-in adapter, NOT an LLM.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { normalizeD1Export } from "../export-d1.mjs";
import { runInvestigations } from "../investigation-pipeline.mjs";
const file = process.argv[2];
if (!file) throw new Error("missing_input");
const raw = await readFile(file,"utf8");
if (raw.length > 2_000_000) throw new Error("export_too_large");
const payload = JSON.parse(raw);
const rows = normalizeD1Export(payload);
if (!rows.length) throw new Error("empty_d1");
const result = await runInvestigations(payload, async brief => {
  const [sourceUrl, observedAt] = brief.sourceReferences[0].split("|");
  return {
    productId: brief.productId,
    thesis: "Hypothetical early collector interest; unverified",
    catalysts: ["Possible demand catalyst, not established"],
    risks: ["No completed sales or volume verified"],
    entryHypothesis: "Investigate prices from independent listings first",
    exitHypothesis: "Reassess after evidence of secondary market liquidity",
    evidence: [
      {kind:"FACT",claim:"Indicative aggregate snapshot exists",sourceUrl,observedAt},
      {kind:"BET",claim:"Future demand is uncertain"}
    ]
  };
});
assert.ok(result.results.length > 0);
assert.ok(result.results.every(r => r.status === "PROPOSAL_REQUIRES_HUMAN_REVIEW"));
assert.ok(result.results.every(r => r.review.purchaseAuthorized === false));
assert.ok(result.results.every(r => r.review.claimSemanticsVerified === false));
console.log("PASS: D1-to-brief-to-deterministic-adapter-to-independent-review; products=" + result.processedProducts);
console.log("Deterministic test adapter only. No model invocation, purchase, prices, or source URLs printed.");
