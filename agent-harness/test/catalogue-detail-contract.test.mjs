import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const grid = await readFile(new URL("../../app/explorer/ExplorerGrid.tsx", import.meta.url), "utf8");
const page = await readFile(new URL("../../app/explorer/catalogue/[language]/[cardId]/page.tsx", import.meta.url), "utf8");
const wrapper = await readFile(new URL("../../app/explorer/page.tsx", import.meta.url), "utf8");
test("catalogue cards open a language-scoped detail and preserve search term", () => {
  assert.match(grid, /\/explorer\/catalogue\//);
  assert.match(grid, /encodeURIComponent\(card\.id\)/);
  assert.match(grid, /encodeURIComponent\(catalogueQuery\)/);
  assert.match(grid, /searchParams\.get\("catalogue"\)/);
  assert.match(wrapper, /<Suspense/);
});
test("catalogue details cannot invent prices or an EDGE investment decision", () => {
  assert.match(page, /readCatalogueQuote\(card\.pricing\)/);
  assert.match(page, /Indication de prix indisponible/);
  assert.match(page, /SUIVI EDGE NON ÉTABLI/);
  assert.match(page, /Aucun dossier EDGE ni correspondance/);
  assert.match(page, /assets\.tcgdex\.net/);
  assert.match(page, /2000000/);
});

test("PRODUCT-001 displays only sourced attributes and no invented investment conclusion", () => {
  assert.match(page, /Caractéristiques vérifiables/);
  assert.match(page, /field\(card\.rarity\)/);
  assert.match(page, /field\(card\.illustrator\)/);
  assert.match(page, /field\(card\.category\)/);
  assert.match(page, /Non renseigné/);
  assert.match(page, /INTELLIGENCE EDGE · À CONNECTER/);
  assert.match(page, /aucun signal BUY|Aucun signal BUY/);
});

test("marketplace search uses the catalogue identity and keeps Gemini user-initiated", async () => {
  const search = await readFile(new URL("../../app/components/MarketplaceSearch.tsx", import.meta.url), "utf8");
  assert.match(page, /marketplaceQuery = \[card\.name, cardNumber, card\.set\?\.name\]/);
  assert.match(page, /<MarketplaceSearch query={marketplaceQuery}/);
  assert.match(search, /vinted\.fr\/catalog/);
  assert.match(search, /leboncoin\.fr\/recherche/);
  assert.match(search, /new URLSearchParams\(\{ search_text: query \}\)/);
  assert.match(search, /aistudio\.google\.com/);
  assert.doesNotMatch(search, /fetch\(/);
});
