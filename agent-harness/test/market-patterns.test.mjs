import test from "node:test";
import assert from "node:assert/strict";
import {recognizePatterns} from "../../app/lib/market-patterns.ts";
const asOf="2026-11-24T12:00:00.000Z";
const fixture=(prior=3,recent=5,price=10000)=>[
 ...Array.from({length:prior},(_,i)=>({lot_id:"prior"+i,variant_key:"v",sold_day:"2026-11-05",price_cents:10000,collected_at:asOf})),
 ...Array.from({length:recent},(_,i)=>({lot_id:"recent"+i,variant_key:"v",sold_day:"2026-11-20",price_cents:price,collected_at:asOf}))
];
test("recognizes rising recorded sales with stable prices",()=>{const [p]=recognizePatterns(fixture(),asOf);assert.equal(p.priorCount,3);assert.equal(p.recentCount,5);assert.equal(p.change,0);});
test("rejects sparse, already repriced or nonaccelerating samples",()=>{for(const rows of [fixture(2,8),fixture(3,5,12000),fixture(5,5)])assert.deepEqual(recognizePatterns(rows,asOf),[]);});
test("rejects future evidence and duplicates",()=>{const rows=fixture(3,4);rows.push({...rows.at(-1)});rows.push({...rows.at(-1),lot_id:"future",collected_at:"2026-11-25T00:00:00.000Z"});assert.deepEqual(recognizePatterns(rows,asOf),[]);});
