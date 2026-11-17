import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const route = await readFile(new URL("../../app/api/catalog/sets/route.ts", import.meta.url), "utf8");
const explorer = await readFile(new URL("../../app/explorer/ExplorerGrid.tsx", import.meta.url), "utf8");
test("extension API is bounded, language-restricted, read-only and price-free", () => {
  assert.match(route, /export async function GET/);
  assert.doesNotMatch(route, /export async function POST/);
  assert.match(route, /LANGUAGES = new Set/);
  assert.match(route, /data.slice\(0, 500\)/);
  assert.match(route, /data.cards.slice\(0, 120\)/);
  assert.match(route, /marketPricesIncluded: false/);
  assert.match(route, /price: null/);
  assert.match(route, /hostname !== IMAGE_HOST/);
});
test("mobile Explorer supports extension drilldown without pretending to have prices", () => {
  assert.match(explorer, /Parcourir les extensions/);
  assert.match(explorer, /\/api\/catalog\/sets\?lang=/);
  assert.match(explorer, /Toutes les extensions/);
  assert.match(explorer, /<CatalogueTilePrice language={card.language} cardId={card.id}/);
  assert.match(explorer, /controller.abort\(\)/);
});
