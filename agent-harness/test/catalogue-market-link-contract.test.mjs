import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const link = await readFile(new URL("../../app/lib/catalogue-market-link.ts", import.meta.url), "utf8");
const page = await readFile(new URL("../../app/explorer/catalogue/[language]/[cardId]/page.tsx", import.meta.url), "utf8");

test("identity bridge requires an exact set-number catalogue ID", () => {
  assert.match(link, /\^\(\[a-zA-Z0-9\]\+\)-\(\[0-9\]\+\)\$/);
  assert.match(link, /pokemon_card_\$\{match\[1\]\}_\$\{match\[2\]\}/);
  assert.match(link, /matches\.length !== 1/);
});
test("unverified language or variants cannot become a verified market price", () => {
  assert.match(link, /CANDIDATE_UNVERIFIED/);
  assert.match(link, /LANGUAGE_VERIFIED_VARIANT_UNKNOWN/);
  assert.match(link, /language === "fr"/);
  assert.match(page, /Correspondance à vérifier/);
  assert.match(page, /aucun prix n’est attribué automatiquement/);
  assert.match(page, /Aucun prix ni conseil d’achat n’est déduit/);
});
test("catalogue detail keeps independent identity and market provenance", () => {
  assert.match(page, /getTcgMarketSnapshot\(\)/);
  assert.match(page, /linkCatalogueToMarket\(cardId, language, snapshot\.cards\)/);
  assert.match(page, /marketLink\.card\.source/);
  assert.match(page, /marketLink\.card\.observedAt/);
  assert.match(page, /marketLink\.card\.priceKind/);
});
