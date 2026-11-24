import test from "node:test";
import assert from "node:assert/strict";
import {learningHorizon,summarizeOutcomes,learningQuery} from "../../app/lib/edge-learning.ts";
test("only supported learning horizons are accepted",()=>{
 for(const n of [7,30,90,365])assert.equal(learningHorizon(String(n)),n);
 for(const v of [null,undefined,"0","999","30 days",["7"]])assert.equal(learningHorizon(v),30);
});
test("outcomes with insufficient sales remain unevaluable and medians are not returns",()=>{
 const base={reason:"PRICE_DROP",lot_id:"a",variant_key:"v",observed_at:"2026-01-01",median_cents:10000,future_count:3,future_median:10000};
 const [g]=summarizeOutcomes([base,{...base,variant_key:"w",future_median:12000},{...base,variant_key:"x",future_median:8000},{...base,variant_key:"y",future_count:2,future_median:100000}]);
 assert.deepEqual(g,{reason:"PRICE_DROP",eligible:4,evaluable:3,up:1,flat:1,down:1,medianChange:0});
});
test("query excludes same-day and self sales, and binds the horizon",()=>{
 assert.match(learningQuery,/s\.sold_day>substr/);
 assert.match(learningQuery,/date\(c\.observed_at,\?\)/);
 assert.match(learningQuery,/s\.lot_id<>'gcc-'\|\|c\.lot_id/);
});
