import assert from "node:assert/strict";
import test from "node:test";
import { analyzeListing, estimateListingMarket, euroCents, rankFixedOffers } from "../../app/lib/listing-analysis.ts";

test("parses euro cents without rounding or treating missing data as free", () => {
  assert.equal(euroCents(" 4,48 "), 448);
  assert.equal(euroCents("0"), 0);
  for (const malformed of ["", "-1", "1.001", "1e2"]) assert.equal(euroCents(malformed), null);
});
test("preserves unknown resale and fees, and clamps the asking limit to cash and gain", () => {
  const input = { askingCents: 3900, acquisitionFeesCents: 448, exitNetCents: null, targetGainCents: 0, budgetCents: 30000 };
  assert.deepEqual(analyzeListing(input), { cost: 4348, gain: null, maxAsk: null, budgetExceeded: false });
  assert.equal(analyzeListing({ ...input, acquisitionFeesCents: null, exitNetCents: 5000 }).maxAsk, null);
  assert.deepEqual(analyzeListing({ ...input, exitNetCents: 5500, targetGainCents: 800, budgetCents: 5000 }),
    { cost: 4348, gain: 1152, maxAsk: 4252, budgetExceeded: false });
  assert.equal(analyzeListing({ ...input, acquisitionFeesCents: null, budgetCents: 3899 }).budgetExceeded, true);
});

test("automatically derives an exit from recent paid sales and keeps a stale singleton descriptive", () => {
  const source = "https://example.com/sale";
  const old = { id: "old", day: "2026-05-27", cents: 175000, source };
  assert.equal(estimateListingMarket([old], "2026-11-18").conservativeNet, null);
  const current = { id: "one", day: "2026-11-15", cents: 20000, source };
  const recent = { id: "two", day: "2026-10-20", cents: 22000, source };
  const result = estimateListingMarket([old, current, recent, recent, { ...current, id: "future", day: "2026-11-19" }], "2026-11-18");
  assert.equal(result.recent.length, 2);
  assert.equal(result.conservativeNet, 18000);
  assert.equal(result.medianGross, 21000);
  assert.equal(result.historicalLow, 20000);
});


test("scanner ranks exact fixed-price leads without capital filtering or self-comparison", () => {
  const paidSales = [
    {id:"a",day:"2026-11-15",cents:200000,source:"https://example.com/a"},
    {id:"b",day:"2026-11-10",cents:220000,source:"https://example.com/b"},
    {id:"gcc-self",day:"2026-11-20",cents:999999,source:"https://gradedcardcenter.com/item/self"},
  ];
  const offers = [
    {id:"self",variantKey:"exact",cents:150000},
    {id:"other",variantKey:"missing",cents:100},
    {id:"expensive",variantKey:"exact",cents:1000000},
    {id:"unknown",variantKey:null,cents:100},
    {id:"self",variantKey:"exact",cents:150000},
  ];
  const ranked = rankFixedOffers(offers,[{key:"exact",paidSales}],"2026-11-24");
  assert.equal(ranked.length,1);
  assert.equal(ranked[0].offer.id,"self");
  assert.equal(ranked[0].medianCents,210000);
  assert.equal(ranked[0].comparableCount,2);
  assert.equal(ranked[0].ceilingBeforeAcquisitionFees,180000);
  assert.equal(ranked[0].headroomCents,30000);
});

test("scanner does not fabricate a reference from a single or stale sale", () => {
  const offers = [{id:"one",variantKey:"exact",cents:100}];
  const paidSales = [{id:"a",day:"2026-11-20",cents:1000,source:"https://example.com/a"},{id:"b",day:"2026-05-01",cents:2000,source:"https://example.com/b"}];
  assert.deepEqual(rankFixedOffers(offers,[{key:"exact",paidSales}],"2026-11-24"),[]);
});
