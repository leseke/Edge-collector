import test from "node:test";
import assert from "node:assert/strict";
import { scanFixedOffers } from "../../../app/lib/fixed-offer-pages.ts";

const page = (page, nextCursor, ids) => ({page,nextCursor,items:ids.map(id=>({id})),checkedAt:"2026-11-18T20:00:00Z"});
test("includes eighth page, deduplicates overlapping listings and reports limit", async () => {
  let n = 0;
  const r = await scanFixedOffers(async cursor => {
    assert.equal(cursor,n === 0 ? null : String(n)); n++;
    return page(n,String(n),["overlap","lot"+n]);
  });
  assert.equal(r.pages,8); assert.equal(r.items.length,9); assert.equal(r.items.at(-1).id,"lot8"); assert.equal(r.status,"limit");
});
test("distinguishes end, failure and repeated cursor without discarding earlier pages", async () => {
  for (const [last,status] of [[null,"partial"],[page(2,null,[]),"end"],[page(2,"loop",[]),"partial"]]) {
    const r=await scanFixedOffers(async cursor=>cursor ? last : page(1,"loop",["one"]));
    assert.equal(r.status,status);assert.equal(r.items[0].id,"one");
  }
});
