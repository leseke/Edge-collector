import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read = path => readFile(new URL(path, import.meta.url), "utf8");
const [explorer, image, shell, home] = await Promise.all([
  read("../../app/explorer/ExplorerGrid.tsx"),
  read("../../app/components/AssetImage.tsx"),
  read("../../app/components/AppShell.tsx"),
  read("../../app/components/MarketDashboard.tsx")
]);
test("Explorer filters observed snapshot products only", () => {
  assert.match(explorer, /cards\.filter/);
  assert.match(explorer, /setQuery/);
  assert.match(explorer, /setSeries/);
  assert.match(explorer, /ni prix fictifs ni offres non vérifiées/);
  assert.doesNotMatch(explorer, /Math\.random|mockProducts|demoCards/);
});
test("Broken image is replaced by a visible fallback", () => {
  assert.match(image, /onError/);
  assert.match(image, /setIndex\(previous => previous \+ 1\)/);
  assert.match(image, /Image non référencée/);
  assert.match(image, /Image inaccessible/);
  assert.match(home, /<AssetImage/);
  assert.match(explorer, /<AssetImage/);
});
test("Explorer is reachable from actual navigation", () => {
  assert.match(shell, /href: "\/explorer"/);
  assert.match(home, /href="\/explorer"/);
  assert.match(shell, /href: "\/mri"/);
});
