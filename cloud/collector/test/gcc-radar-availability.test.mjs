import assert from "node:assert/strict";
import test from "node:test";
import { gccCursor, gccPageUrl, readGccPage } from "../../../app/lib/gcc-active-listings.ts";

const now = new Date("2026-11-18T19:04:00Z");
const info = { currentPage: 2, nextCursor: "valid_cursor_3", counts: { total: 42, auctionCount: 40, fixedPriceCount: 2 } };
const item = { title: "Ectoplasma", subtitle: "Pokemon • French • 2021 • Poing de Fusion", rectoImageKey: "item/example", collectible: { category: "Pokemon", set: "Poing de Fusion" } };
const row = { id: "01234567-89ab-4cde-8fab-0123456789ab", status: "ON_SALE", sellingType: "FIXED_PRICE", priceInCents: 125050, item };

test("catalogue forwards opaque cursors and the exact sales series", () => {
  const url = gccPageUrl("closed", "valid_cursor_2", "Héros Transcendants");
  assert.deepEqual(url.searchParams.getAll("status"), ["SOLD", "WAITING_FOR_PAYMENT"]);
  assert.equal(url.searchParams.get("sets"), "Héros Transcendants");
  assert.equal(url.searchParams.get("cursor"), "valid_cursor_2");
  assert.equal(gccCursor(["valid_cursor_2"]), null);
  assert.equal(gccCursor("invalid?cursor"), null);
});

test("catalogue retains source page metadata and exposes only public listing fields", () => {
  const page = readGccPage({ info, results: [{ ...row, seller: { displayName: "ignored" } }] }, "fixed", now);
  assert.equal(page.page, 2);
  assert.equal(page.nextCursor, "valid_cursor_3");
  assert.equal(page.total, 2);
  assert.equal(page.items[0].cents, 125050);
  assert.match(page.items[0].variant, /^Français/);
  assert.equal(page.items[0].series, "Poing de Fusion");
  assert.ok(!("seller" in page.items[0]));
});
test("auction expiry and closed payment statuses remain distinct", () => {
  const auction = { ...row, sellingType: "PRIVATE", endTime: "2026-11-18T19:05:00Z" };
  assert.equal(readGccPage({ info, results: [auction] }, "auction", now).items.length, 1);
  assert.deepEqual(readGccPage({ info, results: [auction] }, "auction", new Date(auction.endTime)).items, []);
  assert.deepEqual(readGccPage({ info, results: [row] }, "closed", now).items, []);
  const closing = { ...auction, status: "WAITING_FOR_PAYMENT", soldAt: "2026-11-18T19:00:00Z" };
  assert.equal(readGccPage({ info, results: [closing] }, "closed", now).items[0].awaitingPayment, true);
});
