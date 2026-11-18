import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

const hook = registerHooks({
  resolve(name, context, next) {
    return next(name === "./paid-sales" ? "./paid-sales.ts" : name, context);
  },
});
const { publicAuctionPage, publicLotIds, collectPublicGccLots } = await import("../src/gcc-public.ts");
hook.deregister();

const id = "8c29e2ba-d560-49b9-945b-6a8ac21a8978";
const href = '<a href="/item/' + id + '">lot</a>';
const site = "https://gradedcardcenter.com/item/";
const paid = `Article vendu PCA 9 Noctali VMax Pokemon • French • 2021 • Evolution Celeste • Unlimited • #215/203
Prix de vente 1'750€ 27/05/2026 Statut du paiement Payé`;

test("extracts and deduplicates only direct public lot links", () => {
  assert.deepEqual(publicLotIds(href + href + '<a href="https://example.com/item/' + id + '">other</a>'), [id]);
});

test("queues active auctions, rechecks and stores a paid variant without duplication", async () => {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../schema.sql",import.meta.url),"utf8"));
  let active = true;
  let requests = 0;
  const env = {
    DB: { prepare(query) { return { bind(...args) { return {
      async run() { return { meta: db.prepare(query).run(...args) }; },
      async all() { return { results: db.prepare(query).all(...args) }; },
    }; } }; } },
  };
  const fetchPage = async url => {
    requests++;
    assert.ok(url === publicAuctionPage || url === site + id);
    return new Response(url === publicAuctionPage ? href : active ? "Enchère en cours" : paid,
      { headers: { "Content-Type": "text/html; charset=utf-8" } });
  };
  const day = Date.parse("2026-11-18T00:00:00Z");
  await collectPublicGccLots(env, day, fetchPage);
  await collectPublicGccLots(env, day, fetchPage);
  assert.equal(requests, 2);
  assert.equal(db.prepare("SELECT COUNT(*) n FROM paid_market_sales").get().n, 0);
  active = false;
  await collectPublicGccLots(env, day + 86400000, fetchPage);
  await collectPublicGccLots(env, day + 2 * 86400000, fetchPage);
  assert.equal(requests, 5);
  assert.equal(db.prepare("SELECT COUNT(*) n FROM paid_market_sales").get().n, 1);
  const sale = db.prepare("SELECT variant_key,price_cents FROM paid_market_sales").get();
  assert.equal(sale.variant_key, "swsh7-215:fr:unlimited:pca:9");
  assert.equal(sale.price_cents, 175000);
  db.close();
});
