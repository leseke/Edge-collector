import test from "node:test";
import assert from "node:assert/strict";
import {absorptionRate,absorptionQuery} from "../../app/lib/market-absorption.ts";
test("documented rate uses the entire cohort denominator",()=>{
 const row={variant_key:"v",title:"fixture",cohort_count:40,paid_count:30,median_delay_days:3.5};
 assert.equal(absorptionRate(row),75);
 assert.equal(absorptionRate({...row,paid_count:0}),0);
 assert.equal(absorptionRate({...row,cohort_count:0}),null);
});
test("query requires exact lot and variant, payment evidence and a prior complete traversal",()=>{
 assert.match(absorptionQuery,/s\.lot_id='gcc-'\|\|c\.lot_id/);
 assert.match(absorptionQuery,/s\.variant_key=c\.variant_key/);
 assert.match(absorptionQuery,/s\.sold_day>substr\(c\.first_at,1,10\)/);
 assert.match(absorptionQuery,/s\.sold_day<=date\(c\.first_at,'\+14 days'\)/);
 assert.match(absorptionQuery,/gcc_complete_cycles/);
 assert.match(absorptionQuery,/LEFT JOIN paid_market_sales/);
});
