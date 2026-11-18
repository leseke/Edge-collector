import assert from "node:assert/strict";
import test from "node:test";
import { estimateDeliveredCost } from "../../../app/lib/delivered-cost.ts";
import { readGccPage } from "../../../app/lib/gcc-active-listings.ts";

test("single-item Colissimo estimate uses the listing price as declared value", () => {
  assert.deepEqual(estimateDeliveredCost(10000), { insurance: 100, estimate: 11300 });
  assert.deepEqual(estimateDeliveredCost(8050), { insurance: 81, estimate: 9331 });
  for (const price of [null, 0, -1, 1.5, Number.MAX_SAFE_INTEGER]) assert.equal(estimateDeliveredCost(price), null);
});

test("auction uses the next bid supplied by GCC, including when missing", () => {
  const row = { id: "01234567-89ab-4cde-8fab-0123456789ab", status: "ON_SALE", sellingType: "PRIVATE", priceInCents: 1000,
    endTime: "2026-11-20T20:00:00Z", item: { title: "Carte", collectible: {category: "Pokemon"} } };
  const read = (nextPriceInCents) => readGccPage({info:{currentPage:1}, results:[{...row,nextPriceInCents}]}, "auction", new Date("2026-11-18")).items[0];
  assert.equal(read(1100).nextBidCents, 1100);
  assert.equal(read(undefined).nextBidCents, null);
});
