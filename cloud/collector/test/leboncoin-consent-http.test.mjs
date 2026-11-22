import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createOutlookConsentHandler} from "../src/leboncoin-consent-http.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const clientId="123e4567-e89b-12d3-a456-426614174000";
const redirectUri="https://edge.example.com/auth/microsoft/callback";
const sessionId="verified_session_id_1234567890";
function fixture(){
  const pending=new Map(),saved=[];
  const stores={pendingStore:{
    async create(row){pending.set(row.stateHash,row)},
    async consume(stateHash){const row=pending.get(stateHash);pending.delete(stateHash);return row||null}
  },credentialStore:{async save(token){saved.push(token)}}};
  let exchanged=0;
  const handler=createOutlookConsentHandler({enabled:true,redirectUri,clientId,
    clientSecret:"private-client-secret",
    verifySession:async()=>({authenticated:true,sessionId}),
    getStores:async()=>stores,
    fetchImpl:async(url)=>{
      if(url.startsWith("https://graph.microsoft.com/"))return {ok:true,json:async()=>({id:"verified-microsoft-id"})};
      exchanged++;return {ok:true,json:async()=>({
      access_token:"access",refresh_token:"refresh-secret",expires_in:3600})}}
  });
  return {handler,pending,saved,get exchanged(){return exchanged}};
}
const request=(path,method="GET")=>new Request("https://edge.example.com"+path,{method});
test("disabled routes remain closed and never request identity",async()=>{
  let called=false;
  const handler=createOutlookConsentHandler({enabled:false,
    redirectUri,verifySession:async()=>{called=true}});
  const res=await handler(request("/auth/microsoft/start"));
  assert.equal(res.status,404);
  assert.equal(called,false);
});
test("start requires trusted authenticated session",async()=>{
  const handler=createOutlookConsentHandler({enabled:true,redirectUri,clientId,
    verifySession:async()=>({authenticated:false,sessionId}),
    getStores:async()=>{throw Error("should not open")}}
  );
  const res=await handler(request("/auth/microsoft/start"));
  assert.equal(res.status,401);
});
test("rejects cross-origin, unexpected query, and unsafe HTTP methods",async()=>{
  const f=fixture();
  assert.equal((await f.handler(new Request("https://evil.example/auth/microsoft/start"))).status,404);
  assert.equal((await f.handler(request("/auth/microsoft/start?next=https://evil.example"))).status,400);
  assert.equal((await f.handler(request("/auth/microsoft/start","POST"))).status,405);
  assert.equal(f.pending.size,0);
});
test("happy path does not expose access or refresh token and rejects replay",async()=>{
  const f=fixture();
  const start=await f.handler(request("/auth/microsoft/start"));
  assert.equal(start.status,302);
  assert.equal(start.headers.get("cache-control"),"no-store, private");
  assert.equal(start.headers.get("referrer-policy"),"no-referrer");
  const target=new URL(start.headers.get("location"));
  assert.equal(target.hostname,"login.microsoftonline.com");
  const state=target.searchParams.get("state");
  const code="authorization-code-1234";
  const path="/auth/microsoft/callback?state="+encodeURIComponent(state)+"&code="+encodeURIComponent(code);
  const done=await f.handler(request(path));
  assert.equal(done.status,200);
  assert.deepEqual(await done.json(),{connected:true});
  assert.deepEqual(f.saved,[{refreshToken:"refresh-secret",accountId:"verified-microsoft-id"}]);
  const replay=await f.handler(request(path));
  assert.equal(replay.status,400);
  assert.equal(f.exchanged,1);
});
test("rejects malformed and duplicate callback params before exchanging code",async()=>{
  const f=fixture();
  const res=await f.handler(request("/auth/microsoft/callback?code=abc&state=x&state=y"));
  assert.equal(res.status,400);
  assert.equal(f.exchanged,0);
});
test("identity provider denial fails without token exchange",async()=>{
  const f=fixture();
  const res=await f.handler(request("/auth/microsoft/callback?error=access_denied&state=abc"));
  assert.equal(res.status,400);
  assert.equal(f.exchanged,0);
});

test("Graph identity failure cannot persist refresh credentials",async()=>{
  const pending=new Map(),saved=[];
  const handler=createOutlookConsentHandler({enabled:true,redirectUri,clientId,
    clientSecret:"private",verifySession:async()=>({authenticated:true,sessionId}),
    getStores:async()=>({pendingStore:{
      async create(item){pending.set(item.stateHash,item)},
      async consume(key){const item=pending.get(key);pending.delete(key);return item||null}
    },credentialStore:{async save(item){saved.push(item)}}}),
    fetchImpl:async url=>url.startsWith("https://graph.microsoft.com/")
      ? {ok:false,status:403} : {ok:true,json:async()=>({
        access_token:"access",refresh_token:"refresh",expires_in:3600})}
  });
  const start=await handler(request("/auth/microsoft/start"));
  const state=new URL(start.headers.get("location")).searchParams.get("state");
  const res=await handler(request("/auth/microsoft/callback?code=valid-code-123&state="+state));
  assert.equal(res.status,502);
  assert.deepEqual(saved,[]);
});
