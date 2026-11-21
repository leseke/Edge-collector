import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {resolve,dirname} from "node:path";
import outlookWorker from "../src/outlook-worker.ts";

const here=dirname(fileURLToPath(import.meta.url));
const path=resolve(here,"../wrangler.outlook.jsonc");
const cfg=JSON.parse(readFileSync(path,"utf8"));
test("Outlook uses isolated entrypoint, not TCG or Next.js, without cron",()=>{
  assert.equal(cfg.name,"edge-outlook-collector");
  assert.equal(cfg.main,"src/outlook-worker.ts");
  assert.equal(cfg.workers_dev,true);
  assert.equal(cfg.preview_urls,false);
  assert.equal(Object.hasOwn(cfg,"triggers"),false);
  assert.equal(Object.hasOwn(cfg,"d1_databases"),false);
  assert.equal(Object.hasOwn(cfg,"assets"),false);
  assert.equal(Object.hasOwn(cfg,"routes"),false);
});
test("every Outlook route/collection/schedule feature explicitly defaults off",()=>{
  for(const key of [
    "OUTLOOK_ROUTES_ENABLED","OUTLOOK_CONSENT_ENABLED",
    "OUTLOOK_DIAGNOSTICS_ENABLED","OUTLOOK_OFFERS_ENABLED",
    "OUTLOOK_INGEST_ENABLED","OUTLOOK_MANUAL_SYNC_ENABLED",
    "OUTLOOK_SCHEDULE_ENABLED"
  ])assert.equal(cfg.vars[key],"false",key);
  assert.ok(Object.keys(cfg.vars).every(key=>key.startsWith("OUTLOOK_")));
  assert.ok(!JSON.stringify(cfg).includes("OUTLOOK_CLIENT_SECRET"));
  assert.ok(!JSON.stringify(cfg).includes("OUTLOOK_ENCRYPTION_KEY"));
});
test("new Worker with default config rejects OAuth, sync, diagnostics and collection",async()=>{
  for(const route of [
    "/","/auth/microsoft/start","/auth/microsoft/callback",
    "/internal/outlook/offers","/internal/outlook/readiness",
    "/internal/outlook/sync","/internal/collect"
  ]){
    const response=await outlookWorker.fetch(
      new Request("https://edge-outlook-collector.example.test"+route),
      cfg.vars
    );
    assert.equal(response.status,404,route);
    assert.equal(response.headers.get("Cache-Control"),"no-store, private");
    assert.deepEqual(await response.json(),{error:"not_found"});
  }
});
test("dedicated entrypoint has no scheduled processing hook",()=>{
  assert.equal(Object.hasOwn(outlookWorker,"scheduled"),false);
});
