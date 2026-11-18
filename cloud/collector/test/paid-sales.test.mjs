import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (["./card-liquidity", "./marketplace-captures", "./market-trends"].includes(specifier)) return nextResolve(specifier + ".ts", context);
    return nextResolve(specifier, context);
  },
});
const { candidateLots, candidateLeads, discoveryLane, readPaidLot, collectPaidSales } = await import("../src/paid-sales.ts");
const { readRadarPaidSales } = await import("../../../app/lib/radar-paid-sales.ts");
const { estimateListingMarket } = await import("../../../app/lib/listing-analysis.ts");
const { compareMarketWindows } = await import("../../../app/lib/market-trends.ts");
hooks.deregister();

const id = "11111111-2222-3333-4444-555555555555";
const itemUrl = "https://gradedcardcenter.com/item/" + id;
const page = `<main><p>Article vendu</p><h1>PSA 10 Ectoplasma VMax</h1>
  <p>Pokemon • French • 2021 • Poing de Fusion • Unlimited • #157/264</p>
  <p>Prix de vente</p><p>180€</p><p>Weekly Auction</p><time>05/11/2026</time>
  <p>Statut du paiement</p><strong>Payé</strong></main>`;

test("only direct lot links are candidates and only the exact paid lot is eligible", () => {
  assert.deepEqual(candidateLots(itemUrl + " " + itemUrl + " https://gradedcardcenter.com/filtres"), [id]);
  const result = readPaidLot(page, id, "2026-11-18");
  assert.equal(result.key, "swsh8-157:fr:unlimited:psa:10");
  assert.equal(result.cents, 18000);
  assert.equal(result.day, "2026-11-05");
  for (const [from, to] of [
    ["157/264", "inconnue"], ["French", "Inconnue"], ["PSA 10", ""],
    ["Unlimited", "édition inconnue"], ["Article vendu", "Enchère en cours"], ["Payé", "En attente"],
    ["Payé", "<script>Payé</script>"], ["Payé", "Payé partiellement"], ["05/11/2026", "31/11/2026"],
    ["05/11/2026", "19/11/2026"], ["05/11/2026", "10/11/2021"],
  ]) assert.equal(readPaidLot(page.replace(from, to), id, "2026-11-18"), null, from);
  for (const [from, to] of [["French", "English"], ["157/264", "271/264"], ["Unlimited", "First Edition"], ["PSA 10", "PSA 9"]]) {
    assert.match(readPaidLot(page.replace(from, to), id, "2026-11-18").key, /^carte:/);
  }
  const booster = page.replace("PSA 10 Ectoplasma VMax", "Booster Poing de Fusion scellé").replace(" • #157/264", "");
  assert.match(readPaidLot(booster, id, "2026-11-18").key, /^booster:/);
  assert.equal(readPaidLot(booster.replace("scellé", "ouvert"), id, "2026-11-18"), null);
});

test("a four-day sweep includes releases, cards, boosters and boxes, and preserves source types", () => {
  assert.deepEqual(new Set(["18", "19", "20", "21"].map(day => discoveryLane("2026-11-" + day).category)),
    new Set(["CARTE", "BOOSTER", "COFFRET", "SORTIE"]));
  const ad = "https://www.leboncoin.fr/ad/collection/123";
  const release = "https://www.pokemon.com/fr/actualites/produits-novembre";
  assert.deepEqual([...candidateLeads(`${ad}?track=test ${release} ${itemUrl} https://evil.example/`)], [
    [itemUrl, "LOT"], [ad, "ANNONCE"], [release, "PUBLICATION"],
  ]);
});

test("trend estimates require same-variant price and volume evidence in both windows", () => {
  const row = (variant_key, sold_day, price_cents) => ({ variant_key, sold_day, price_cents });
  const recent = Array.from({ length: 3 }, (_, i) => row("coffret:a", "2026-11-17", 11500 + i * 100));
  const prior = Array.from({ length: 3 }, (_, i) => row("coffret:a", "2026-10-17", 9900 + i * 100));
  assert.equal(compareMarketWindows([...recent, ...prior.slice(0, 2), row("coffret:b", "2026-10-17", 10000)], "2026-11-18").length, 0);
  const [trend] = compareMarketWindows([...recent, ...prior], "2026-11-18");
  assert.equal(trend.priceChange, 16);
  assert.equal(trend.scenario, "HAUSSIER");
});

test("a native scan and its retry feed the real market calculation through SQLite", async () => {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../schema.sql", import.meta.url), "utf8"));
  const DB = {
    prepare(query) {
      return { bind(...values) {
        return {
          async run() { return { meta: db.prepare(query).run(...values) }; },
          async all() { return { results: db.prepare(query).all(...values) }; },
        };
      } };
    },
  };
  let searches = 0;
  const transport = async (url, options) => {
    if (url === itemUrl) {
      assert.equal(options.headers["x-goog-api-key"], undefined);
      return new Response(page, { headers: { "content-type": "text/html" } });
    }
    searches++;
    return Response.json({ candidates: [{
      finishReason: "STOP",
      groundingMetadata: { webSearchQueries: ["test"] },
      content: { parts: [{ text: itemUrl }] },
    }] });
  };
  const now = new Date("2026-11-18T09:00:00Z");
  await collectPaidSales({ DB }, +now, transport);
  assert.equal(searches, 0);
  const env = { DB, GEMINI_FREE_TIER_ENABLED: "true", GEMINI_API_KEY: "test" };
  await Promise.all([collectPaidSales(env, +now, transport), collectPaidSales(env, +now, transport)]);
  assert.equal(searches, 1);
  await collectPaidSales(env, +now + 86_400_000, transport);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM paid_market_sales").get().n, 1);
  assert.throws(() => db.exec("UPDATE paid_market_sales SET price_cents=1"), /immutable_paid_sale/);

  const { cards, scan } = await readRadarPaidSales(DB, now);
  assert.equal(scan.status, "OK");
  const psa = cards.find(card => card.key === "swsh8-157:fr:unlimited:psa:10");
  const pca = cards.find(card => card.key === "swsh8-157:fr:unlimited:pca:9.5");
  assert.equal(estimateListingMarket(psa.paidSales, "2026-11-18").conservativeGross, 18000);
  assert.equal(estimateListingMarket(pca.paidSales, "2026-11-18").conservativeGross, null);
  db.close();
});
