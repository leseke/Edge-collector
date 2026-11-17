import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const page = await readFile(new URL("../../app/explorer/[productId]/page.tsx", import.meta.url), "utf8");
const explorer = await readFile(new URL("../../app/explorer/ExplorerGrid.tsx", import.meta.url), "utf8");
test("product detail resolves only observed products and rejects unknown IDs", () => {
  assert.match(page, /getTcgMarketSnapshot\(\)/);
  assert.match(page, /snapshot\.cards\.find/);
  assert.match(page, /notFound\(\)/);
  assert.match(page, /productId/);
});
test("product detail discloses uncertainty and provenance without speculative recommendations", () => {
  assert.match(page, /card\.source/);
  assert.match(page, /card\.observedAt/);
  assert.match(page, /pas d'une vente conclue/);
  assert.match(page, /DeepSeek non activé/);
  assert.doesNotMatch(page, /STRONG_BUY|Rendement garanti|fetch\(/);
});
test("explorer provides navigable links to product detail", () => {
  assert.match(explorer, /href=\{\x60\/explorer\/\$\{encodeURIComponent\(card\.productId\)\}\x60\}/);
  assert.match(explorer, /Voir la fiche/);
});
