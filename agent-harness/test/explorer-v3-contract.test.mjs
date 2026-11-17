import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const explorer = await readFile(new URL("../../app/explorer/ExplorerGrid.tsx", import.meta.url), "utf8");
const css = await readFile(new URL("../../app/dashboard.css", import.meta.url), "utf8");
test("category tabs and sealed products explicitly distinguish absent market data", () => {
  assert.match(explorer, /type Category = "cards" \| "sealed"/);
  assert.match(explorer, /aria-pressed=\{category === "sealed"\}/);
  assert.match(explorer, /Aucun produit scellé n'est présent/);
  assert.match(explorer, /ni prix fictifs ni offres non vérifiées/);
});
test("collection navigation and filters use observed card data", () => {
  assert.match(explorer, /new Map<string, TcgCard\[\]>/);
  assert.match(explorer, /setSeries\(name\)/);
  assert.match(explorer, /cards\.filter/);
  assert.match(explorer, /setSort/);
  assert.match(explorer, /Voir le dossier/);
});
test("visual explorer retains responsive layouts and keyboard focus", () => {
  assert.match(css, /edge-series-strip/);
  assert.match(css, /focus-visible/);
  assert.match(css, /edge-explorer-filters-v3/);
});
