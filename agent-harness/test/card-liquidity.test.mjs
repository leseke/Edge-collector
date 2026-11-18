import assert from "node:assert/strict";
import test from "node:test";
import { registerHooks } from "node:module";
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === "./marketplace-captures" && context.parentURL?.endsWith("/card-liquidity.ts")) {
      return nextResolve("./marketplace-captures.ts", context);
    }
    return nextResolve(specifier, context);
  },
});
const { summarizeCardLiquidity, reviewedCardLiquidity } = await import("../../app/lib/card-liquidity.ts");
hooks.deregister();

const [evidence] = reviewedCardLiquidity;
const { estimateListingMarket } = await import("../../app/lib/listing-analysis.ts");

test("reviewed sales remain unique and different graders never combine into a short-term quote", () => {
  const sales = reviewedCardLiquidity.flatMap(card => card.paidSales);
  assert.equal(new Set(sales.map(sale => sale.id)).size, sales.length);
  const cases = reviewedCardLiquidity.filter(card => card.name === "Ectoplasma VMAX 157/264");
  assert.equal(cases.length, 2);
  for (const card of cases) {
    const estimate = estimateListingMarket(card.paidSales, "2026-11-18");
    assert.equal(estimate.recent.length, 1);
    assert.equal(estimate.conservativeNet, null);
    assert.equal(estimate.historicalLow, card.variant.includes("PSA") ? 13000 : null);
  }
});
test("missing listing coverage is unknown and historical paid sales stay dated", () => {
  const result = summarizeCardLiquidity(evidence, "2026-11-18");
  assert.equal(result.active, null);
  assert.equal(result.change, null);
  assert.equal(result.lastPaid.cents, 175000);
  assert.deepEqual(result.saleWindows.map(x => x.observed), [0, 0, 0]);
});

test("inventory comparisons only use the same scope; disappearing listings are not sales", () => {
  const result = summarizeCardLiquidity({ ...evidence, paidSales: [], listings: [
    { day: "2026-11-18", scope: "vinted-fr", listingIds: ["a", "a", "c"] },
    { day: "2026-11-17", scope: "other", listingIds: ["z"] },
    { day: "2026-11-15", scope: "vinted-fr", listingIds: ["a", "b", "d"] },
  ] }, "2026-11-18");
  assert.equal(result.active, 2);
  assert.equal(result.change, -1);
  assert.equal(result.newlyObserved, 1);
  assert.deepEqual(result.saleWindows.map(x => x.observed), [0, 0, 0]);
});

test("paid sales deduplicate by transaction and exclude future records", () => {
  const sale = { ...evidence.paidSales[0], day: "2026-11-14" };
  const result = summarizeCardLiquidity({ ...evidence, paidSales: [sale, sale, { ...sale, id: "future", day: "2026-11-19" }] }, "2026-11-18");
  assert.deepEqual(result.saleWindows.map(x => x.observed), [1, 1, 1]);
});

test("flags only fresh comparable supply declines with resilient paid sales", () => {
  const sales = ["2026-11-17", "2026-11-03", "2026-10-15", "2026-09-29"].map((day, id) =>
    ({ ...evidence.paidSales[0], id: String(id), day }));
  const listings = [
    { day: "2026-11-17", scope: "same", listingIds: ["a"] },
    { day: "2026-11-10", scope: "same", listingIds: ["a", "b"] },
  ];
  const pilot = { ...evidence, paidSales: sales, listings };
  assert.equal(summarizeCardLiquidity(pilot, "2026-11-18").signal, "SUPPLY_TIGHTENING");
  assert.equal(summarizeCardLiquidity({ ...pilot, paidSales: sales.slice(0, 2) }, "2026-11-18").signal, "INSUFFICIENT_EVIDENCE");
  assert.equal(summarizeCardLiquidity({ ...pilot, paidSales: sales.map((sale, id) =>
    id < 2 ? { ...sale, cents: sale.cents - 100 } : sale) }, "2026-11-18").signal, "NO_SIGNAL");
});
