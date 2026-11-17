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
  assert.match(page, /Non collecté/);
  assert.match(page, /SUIVI EDGE NON ÉTABLI/);
  assert.match(page, /Aucun dossier EDGE ni correspondance/);
  assert.match(page, /assets\.tcgdex\.net/);
  assert.match(page, /2000000/);
});
