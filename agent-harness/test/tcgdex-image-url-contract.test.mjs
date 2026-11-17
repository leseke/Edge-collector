import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const market = await readFile(new URL("../../app/lib/market-data.ts", import.meta.url), "utf8");
const image = await readFile(new URL("../../app/components/AssetImage.tsx", import.meta.url), "utf8");

test("TCGdex image base URLs are converted to image files", () => {
  assert.match(market, /\$\{url\.origin\}\$\{path\}\/high\.webp/);
  assert.match(market, /assets\.tcgdex\.net/);
  assert.match(market, /url\.search \|\| url\.hash/);
});
test("image component retries only trusted TCGdex host and exposes an honest fallback", () => {
  assert.match(image, /hostname !== "assets\.tcgdex\.net"/);
  assert.match(image, /low\.webp/);
  assert.match(image, /high\.png/);
  assert.match(image, /onError/);
  assert.match(image, /Image indisponible/);
});
