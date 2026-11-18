import assert from "node:assert/strict";
import test from "node:test";
import { summarizeCardLiquidity, reviewedCardLiquidity } from "../../app/lib/card-liquidity.ts";

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
