// CI-only: actual D1 read-only query output is piped on stdin, never committed.
// The agent runtime receives only the minimized local snapshot, not Cloudflare credentials.
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { normalizeD1Export } from "../export-d1.mjs";
import { apply } from "../plugins/edge-market-tool.ts";
const chunks: Buffer[] = [];
for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
const rows = normalizeD1Export(JSON.parse(Buffer.concat(chunks).toString("utf8")));
if (!rows.length) throw new Error("no_real_observations");
const snapshotPath = fileURLToPath(new URL("../data/observations.json", import.meta.url));
const original = await readFile(snapshotPath, "utf8");
try {
  await writeFile(snapshotPath, JSON.stringify(rows), { mode: 0o600 });
  let tool: any;
  apply({ tools: { register(t: any) { tool = t; } } } as any);
  const ids = [...new Set(rows.map((r: any) => r.product_id))];
  for (const productId of ids) {
    const result = JSON.parse(await tool.execute({ productId }, { signal: new AbortController().signal }));
    assert.equal(result.productId, productId);
    assert.equal(result.purchaseAuthorized, false);
    assert.equal(result.provenance, "INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE");
    assert.ok(result.observations > 0);
  }
  const fixtureMode = process.env.EDGE_DATA_MODE === "FIXTURE";
  console.log("PASS: native EDGE Cordis tool consumed " + (fixtureMode ? "SYNTHETIC LOCAL D1 fixture" : "authentic remote D1") + " rows; products=" + ids.length + ", observations=" + rows.length);
  console.log("No prices, source URLs, Cloudflare credentials or snapshots printed.");
} finally {
  await writeFile(snapshotPath, original);
}
