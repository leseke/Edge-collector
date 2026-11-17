// Executed only in a disposable CI runner with published DeepSeek Harness tool packages.
import assert from "node:assert/strict";
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
