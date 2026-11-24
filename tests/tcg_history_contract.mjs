import assert from "node:assert/strict";
import { indexTcgHistory, compareIndicativePrices } from "../app/lib/tcg-history.ts";
const a = {productId:"pokemon_card_test",snapshotId:"1-1",observedAt:"2025-01-01T12:00:00Z",source:"test",currency:"EUR",priceKind:"aggregate",low:10,availability:"UNKNOWN",sourceUpdatedAt:"2025-01-01",reportSha256:"a".repeat(64)};
const b = {...a,snapshotId:"2-1",observedAt:"2025-01-02T12:00:00Z",sourceUpdatedAt:"2025-01-02",low:15};
assert.deepEqual(indexTcgHistory([b,a,a]).get(a.productId),[a,b]);
assert.equal(compareIndicativePrices(a,b),50);
for (const patch of [{currency:"USD"},{source:"other"},{low:null},{low:0},{sourceUpdatedAt:a.sourceUpdatedAt},{sourceUpdatedAt:null},{priceKind:"sale"},{productId:"pokemon_card_other"}]) {
  assert.equal(compareIndicativePrices(a,{...b,...patch}),null);
}
assert.equal(indexTcgHistory([{...a,low:0}]).get(a.productId)[0].low,null);
assert.equal(indexTcgHistory([{...a,reportSha256:"bad"}]).size,0);
