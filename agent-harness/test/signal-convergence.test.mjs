import test from "node:test";
import assert from "node:assert/strict";
import {convergeSignals} from "../../app/lib/signal-convergence.ts";
const demand=variant=>({variant,priorCount:3,recentCount:6,before:1000,after:1000,change:0,evidence:[]});
const supply=variant_key=>({variant_key,title:"Fixture",prior_count:10,current_count:5,prior_at:"2026-11-10",current_at:"2026-11-20"});
const absorption=variant_key=>({variant_key,title:"Fixture",cohort_count:5,paid_count:3,median_delay_days:4});
test("convergent supply and demand are prioritized before price growth",()=>{
 const result=convergeSignals([demand("a"),demand("b")],[supply("b")],[absorption("b")]);
 assert.equal(result[0].key,"b");assert.equal(result[0].convergence,true);assert.equal(result[0].demand.change,0);assert.equal(result[0].absorption.paid_count,3);assert.equal(result[1].convergence,false);
});
test("different language or grade variants never converge",()=>{
 const result=convergeSignals([demand("card:fr:psa:10")],[supply("card:it:psa:10"),supply("card:fr:psa:9")],[]);
 assert.equal(result.length,3);assert.ok(result.every(x=>!x.convergence));
});
test("missing source is distinct from empty result and isolated signals survive",()=>{
 const result=convergeSignals(null,[supply("a")],[]);
 assert.equal(result.length,1);assert.equal(result[0].coverage.demand,false);assert.equal(result[0].coverage.absorption,true);assert.equal(result[0].convergence,false);
});
test("historical absorption alone is context, not current acceleration",()=>{
 assert.deepEqual(convergeSignals([],[],[absorption("a")]),[]);
});
