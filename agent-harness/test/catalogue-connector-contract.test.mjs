import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const route = await readFile(new URL("../../app/api/catalog/cards/route.ts", import.meta.url), "utf8");
const explorer = await readFile(new URL("../../app/explorer/ExplorerGrid.tsx", import.meta.url), "utf8");
test("catalogue API is read-only, bounded, allowlisted and price-free", () => {
  assert.match(route, /export async function GET/);
  assert.doesNotMatch(route, /export async function POST/);
  assert.match(route, /LANGUAGES = new Set/);
  assert.match(route, /query.length < 2/);
  assert.match(route, /query.length > 60/);
  assert.match(route, /records.slice\(0, 60\)/);
  assert.match(route, /price: null/);
  assert.match(route, /marketPricesIncluded: false/);
  assert.match(route, /hostname !== "assets.tcgdex.net"/);
});
test("catalogue search is separate from observed prices and handles unavailable upstream", () => {
  assert.match(explorer, /\/api\/catalog\/cards\?q=/);
  assert.match(explorer, /Catalogue indisponible/);
  assert.match(explorer, /Prix non collecté/);
  assert.match(explorer, /catalogueLanguage/);
  assert.match(explorer, /controller.abort\(\)/);
});
