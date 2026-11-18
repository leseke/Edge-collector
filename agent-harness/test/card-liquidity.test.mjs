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
