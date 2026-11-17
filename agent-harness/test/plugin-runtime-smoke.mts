// Executed only in a disposable CI runner with published DeepSeek Harness tool packages.
import assert from "node:assert/strict";
import { writeFile, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { apply } from "../plugins/edge-market-tool.ts";

let registered: any;
const context = { tools: { register(tool: any) { registered = tool; return () => {}; } } };
apply(context as any);
assert.equal(registered?.name, "edge_market_snapshot");
const result = await registered.execute({ productId: "pokemon_card_base1_4" }, { signal: new AbortController().signal });
const output = JSON.parse(result);
assert.equal(output.productId, "pokemon_card_base1_4");
assert.equal(output.provenance, "INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE");
assert.equal(output.observations, 0);
assert.equal(output.purchaseAuthorized, false);
console.log("PASS: published dsh-tools registered and executed EDGE read-only tool with empty snapshot");

const snapshotPath = fileURLToPath(new URL("../data/observations.json", import.meta.url));
const original = await readFile(snapshotPath, "utf8");
try {
  // Synthetic fixtures test the plumbing only; these are NOT market observations.
  await writeFile(snapshotPath, JSON.stringify([
    { product_id: "pokemon_card_base1_4", price_kind: "AGGREGATE", currency: "EUR", source_url: "https://api.tcgdex.net/v2/fr/cards/base1-4", observed_at: "2026-11-16T10:00:00Z", price_cents: 1000 },
    { product_id: "pokemon_card_base1_4", price_kind: "AGGREGATE", currency: "EUR", source_url: "https://api.tcgdex.net/v2/fr/cards/base1-4", observed_at: "2026-11-17T10:00:00Z", price_cents: 1100 }
  ]));
  const fixtureResult = JSON.parse(await registered.execute({ productId: "pokemon_card_base1_4" }, { signal: new AbortController().signal }));
  assert.equal(fixtureResult.observations, 2);
  assert.equal(fixtureResult.changePercent, 10);
  assert.equal(fixtureResult.purchaseAuthorized, false);
  console.log("PASS: native tool processes a two-observation SYNTHETIC fixture; not real market data");
} finally {
  await writeFile(snapshotPath, original);
}
