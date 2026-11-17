import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const root = new URL("../../", import.meta.url);
const read = async path => readFile(new URL(path,root),"utf8");
test("required governance documents and ADR sections are present",async()=>{
 for(const path of ["AGENTS.md","SPEC.md","docs/CONTRAT.md","STATE.md"]) {
  const content=await read(path);
  assert.ok(content.length>100,path);
 }
 const adr=await read("docs/adr/001-preserve-existing-collector.md");
 for(const heading of ["Context","Options","Decision","Rationale","Consequences","Reversibility"]) assert.match(adr,new RegExp("## "+heading));
});
test("contracts explicitly distinguish existing schema and proposed review API",async()=>{
 const contract=await read("docs/CONTRAT.md");
 const schema=await read("cloud/collector/schema.sql");
 assert.match(schema,/CREATE TABLE IF NOT EXISTS observations/);
 assert.doesNotMatch(schema,/CREATE TABLE IF NOT EXISTS review_queue/);
 assert.match(contract,/NOT implemented/);
 assert.match(contract,/No review_queue or investigations table/);
 assert.match(contract,/claimSemanticsVerified: false/);
});
test("governance prohibits autonomous purchases and unapproved production promotion",async()=>{
 const agents=await read("AGENTS.md");
 const spec=await read("SPEC.md");
 assert.match(agents,/Never modify main, deploy, merge, purchase/);
 assert.match(spec,/no autonomous checkout, ordering, or payment/);
});
