import test from "node:test";
import assert from "node:assert/strict";
import {scoreLeboncoinLead,sortLeboncoinLeads} from "../src/leboncoin-lead-triage.mjs";
const now=Date.parse("2026-11-20T11:00:00Z");
const row={listing_id:"leboncoin:101",observed_at:"2026-11-20T09:00:00Z",
  alert_hits:2,first_price_cents:15000,price_cents:13000};
test("recent repeated listing with significant asking-price drop gets investigation priority",()=>{
  const result=scoreLeboncoinLead(row,now);
  assert.equal(result.kind,"PRICE_DROP");
  assert.equal(result.changeCents,-2000);
  assert.ok(result.changePercent>13 && result.changePercent<14);
  assert.match(result.label,/à examiner/);
});
test("small price changes and non-decreases never produce a buy claim",()=>{
  assert.equal(scoreLeboncoinLead({...row,price_cents:14800},now).kind,"REPEATED");
  assert.equal(scoreLeboncoinLead({...row,price_cents:15500},now).kind,"REPEATED");
  assert.equal(scoreLeboncoinLead({...row,alert_hits:1},now).kind,"OBSERVED");
  assert.equal(scoreLeboncoinLead({...row,first_price_cents:null},now).kind,"REPEATED");
  assert.equal(scoreLeboncoinLead({...row,first_price_cents:0},now).kind,"REPEATED");
});
test("stale or future-dated records cannot receive a fresh price-drop signal",()=>{
  assert.equal(scoreLeboncoinLead({...row,observed_at:"2026-11-17T09:00:00Z"},now).kind,"OBSERVED");
  assert.equal(scoreLeboncoinLead({...row,observed_at:"2026-11-21T09:00:00Z"},now).kind,"OBSERVED");
});
test("prioritize significant drop over repetition, and both over unverified one-off",()=>{
  const input=[
    {...row,listing_id:"leboncoin:201",alert_hits:1},
    {...row,listing_id:"leboncoin:202",price_cents:15000},
    {...row,listing_id:"leboncoin:203",price_cents:12000},
    {...row,listing_id:"leboncoin:204",price_cents:13000},
  ];
  assert.deepEqual(sortLeboncoinLeads(input,now).map(x=>x.listing_id),
    ["leboncoin:203","leboncoin:204","leboncoin:202","leboncoin:201"]);
  assert.deepEqual(input.map(x=>x.listing_id),[
    "leboncoin:201","leboncoin:202","leboncoin:203","leboncoin:204"]);
});
test("no inferred return, liquidity, sold status or current availability",()=>{
  const serialized=JSON.stringify(scoreLeboncoinLead(row,now));
  assert.doesNotMatch(serialized,/BUY|SOLD|AVAILABLE|profit|guarantee/i);
});
