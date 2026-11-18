import assert from "node:assert/strict";
import test from "node:test";
import { registerHooks } from "node:module";
const hook = registerHooks({
  resolve(name, context, next) {
    return next(["./comparable-sales", "./delivered-cost"].includes(name) ? name + ".ts" : name, context);
  },
});
const { rankFixedOffers } = await import("../../../app/lib/fixed-offer-ranking.ts");
hook.deregister();
const item = { title:"PSA 10 Noctali VMAX", series:"Évolution Céleste", variant:"Français • 2021 • Évolution Céleste • Unlimited • #215/203", comparableCard:true, id:"a", cents:10000 };
const sale = (id, day, cents) => ({id,day,cents,source:"example"});
const group = (key, paidSales) => ({key, paidSales});
const key = "swsh7-215:fr:unlimited:psa:10";
const today = "2026-11-18";
test("rank delivered discounts, preserve single references and require eligible items", () => {
  const sales=[sale("1",today,12000),sale("2",today,14000)];
  const run=(items,rows)=>rankFixedOffers(items,[group(key,rows)],today);
  const ranked=run([item,{...item,id:"b",cents:9000},{...item,id:"c",comparableCard:false}],sales);
  assert.deepEqual(ranked.map(x=>x.item.id),["b","a"]);
  assert.equal(ranked[1].gap,1700);
  assert.equal(run([item],sales.slice(0,1))[0].reason,"single");
  assert.equal(run([{...item,cents:14000}],sales).length,0);
});
test("series signal counts distinct sales in successive weeks", () => {
  const rows=["1","2","3"].map(id=>sale(id,today,1000));
  const run=rows=>rankFixedOffers([item],[group(key.replace("psa:10","pca:9"),rows)],today);
  assert.equal(run([...rows,rows[0]])[0].recent,3);
  assert.equal(run(rows)[0].reason,"series");
  assert.equal(run([...rows,sale("4","2026-11-11",100),sale("5","2026-11-10",100)]).length,0);
});
