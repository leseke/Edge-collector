import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { normalizeD1Export } from "./export-d1.mjs";
import { prepareInvestigationBrief } from "./agent-brief.mjs";
const input = process.argv[2];
if (!input) throw new Error("missing_input");
const raw = await readFile(input,"utf8");
if (raw.length > 2_000_000) throw new Error("export_too_large");
const payload = JSON.parse(raw);
const rows = normalizeD1Export(payload);
const ids = [...new Set(rows.map(r=>r.product_id))];
if (!ids.length) throw new Error("no_products");
for (const id of ids) {
  const brief = prepareInvestigationBrief(payload,id);
  assert.equal(brief.productId,id);
  assert.equal(brief.purchaseAuthorized,false);
  assert.ok(brief.sourceReferences.length);
  assert.ok(brief.missingEvidence.includes("NO_COMPLETED_SALES_OR_VOLUME_EVIDENCE"));
}
console.log("PASS: real D1 observations prepared for " + ids.length + " scoped AI briefs, no model call, no market prices or secrets printed");
