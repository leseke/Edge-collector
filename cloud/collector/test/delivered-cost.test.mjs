import assert from "node:assert/strict";
import test from "node:test";
import { amountInCents, deliveredCost } from "../../../app/lib/delivered-cost.ts";
import { readGccPage } from "../../../app/lib/gcc-active-listings.ts";

test("total uses confirmed costs including explicit zero and French decimal input", () => {
  assert.equal(deliveredCost(10000, "0", "12,50"), 11250);
  assert.equal(deliveredCost(10000, "1.25", "0"), 10125);
  assert.equal(deliveredCost(10000, "0", ""), null);
  assert.equal(deliveredCost(null, "0", "0"), null);
  for (const value of ["", "-1", "1,234", "1e4", "abc"]) assert.equal(amountInCents(value), null);
});

test("auction uses the next bid supplied by GCC, including when missing", () => {
  const row = { id: "01234567-89ab-4cde-8fab-0123456789ab", status: "ON_SALE", sellingType: "PRIVATE", priceInCents: 1000,
    endTime: "2026-11-20T20:00:00Z", item: { title: "Carte", collectible: {category: "Pokemon"} } };
  const read = (nextPriceInCents) => readGccPage({info:{currentPage:1}, results:[{...row,nextPriceInCents}]}, "auction", new Date("2026-11-18")).items[0];
  assert.equal(read(1100).nextBidCents, 1100);
  assert.equal(read(undefined).nextBidCents, null);
});
