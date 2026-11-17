import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { registerHooks } from "node:module";

const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "./product-variant" && context.parentURL?.endsWith("/catalogue-market-link.ts")) {
      return nextResolve("./product-variant.ts", context);
    }
    return nextResolve(specifier, context);
  },
});
const { linkCatalogueToMarket } = await import("../../app/lib/catalogue-market-link.ts");
const { marketVariant } = await import("../../app/lib/product-variant.ts");
hooks.deregister();

const recorded = value => ({ value, source: "https://example.com/market-observation" });
const legacyCard = { productId: "pokemon_card_base1_4", languageVerified: true };
const snapshotCard = { productId: "pokemon_card_base1-4", languageVerified: false };

test("accepts both exact product ID formats and rejects ambiguous or invalid identities", () => {
  assert.equal(linkCatalogueToMarket("base1-4", "fr", [legacyCard]).productId, legacyCard.productId);
  assert.equal(linkCatalogueToMarket("base1-4", "fr", [snapshotCard]).productId, snapshotCard.productId);
  assert.equal(linkCatalogueToMarket("base1-4", "fr", [legacyCard, snapshotCard]).status, "NO_MATCH");
  assert.equal(linkCatalogueToMarket("base1/4", "fr", [snapshotCard]).status, "NO_MATCH");
});

test("matches compatible evidence provisionally and rejects explicit language conflicts", () => {
  const variant = marketVariant({
    language: recorded("fr"), edition: recorded("FIRST_EDITION"), condition: recorded("NM"),
    grading: recorded("PSA"), grade: recorded("9.5"),
  });
  const card = { ...snapshotCard, variant };
  const link = linkCatalogueToMarket("base1-4", "fr", [card]);
  assert.equal(link.status, "CANDIDATE_UNVERIFIED");
  assert.deepEqual(Object.values(link.variant).map(evidence => evidence.value), ["fr", "FIRST_EDITION", "NM", "PSA", "9.5"]);
  assert.deepEqual(link.variant.grade, { status: "VERIFIED", ...recorded("9.5") });
  assert.equal(linkCatalogueToMarket("base1-4", "en", [card]).status, "NO_MATCH");
});

test("keeps legacy, malformed, and inapplicable evidence unknown", () => {
  const link = linkCatalogueToMarket("base1-4", "fr", [legacyCard]);
  assert.equal(link.status, "CANDIDATE_UNVERIFIED");
  assert.ok(Object.values(link.variant).every(evidence => evidence.status === "UNKNOWN"));
  const result = marketVariant({
    language: { value: "fr", source: "javascript:alert(1)" },
    edition: { value: "FIRST_EDITION" }, condition: recorded("mint"),
    grading: recorded("RAW"), grade: recorded("10"),
  });
  assert.equal(result.grading.value, "RAW");
  for (const key of ["language", "edition", "condition", "grade"]) {
    assert.deepEqual(result[key], { status: "UNKNOWN", value: null, source: null });
  }
});

test("catalogue detail keeps market provenance and withholds attribution and advice", async () => {
  const page = await readFile(new URL("../../app/explorer/catalogue/[language]/[cardId]/page.tsx", import.meta.url), "utf8");
  assert.match(page, /getTcgMarketSnapshot\(\)/);
  assert.match(page, /linkCatalogueToMarket\(cardId, language, snapshot\.cards\)/);
  assert.match(page, /marketLink\.card\.source/);
  assert.match(page, /marketLink\.card\.observedAt/);
  assert.match(page, /marketLink\.card\.priceKind/);
  assert.match(page, /aucun prix n’est attribué automatiquement/);
  assert.match(page, /Aucun prix ni conseil d’achat n’est déduit/);
});
