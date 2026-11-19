import test from "node:test";
import assert from "node:assert/strict";
import {refreshMicrosoftGraphToken,runWithMicrosoftToken} from "../src/leboncoin-oauth.mjs";
const clientId="123e4567-e89b-12d3-a456-426614174000";
test("refresh requests only delegated minimal scopes",async()=>{
  let called=false;
  const r=await refreshMicrosoftGraphToken({clientId,clientSecret:"fixture-secret",
    refreshToken:"fixture-refresh",fetchImpl:async (url,options)=>{
      called=true;
      assert.match(url,/login.microsoftonline.com\/consumers\/oauth2\/v2.0\/token/);
      assert.equal(options.method,"POST");
      const data=new URLSearchParams(options.body);
      assert.equal(data.get("grant_type"),"refresh_token");
      assert.equal(data.get("scope"),"offline_access Mail.Read");
      assert.equal(data.get("refresh_token"),"fixture-refresh");
      return {ok:true,json:async()=>({access_token:"fixture-access",refresh_token:"next-refresh",expires_in:3600})};
    }});
  assert.equal(called,true);
  assert.equal(r.replacementRefreshToken,"next-refresh");
  assert.equal(r.expiresInSeconds,3600);
});
test("rotated refresh token stored before invoking Graph consumer",async()=>{
  const events=[];
  const result=await runWithMicrosoftToken({
    clientId,clientSecret:"fixture-secret",
    credentialStore:{
      load:async()=>({refreshToken:"fixture-refresh"}),
      save:async()=>{events.push("stored")}
    },
    fetchImpl:async()=>({ok:true,json:async()=>({
      access_token:"fixture-access",refresh_token:"rotated",expires_in:3600
    })}),
    run:async token=>{events.push("run");assert.equal(token,"fixture-access");return 42}
  });
  assert.equal(result,42);
  assert.deepEqual(events,["stored","run"]);
});
test("fail closed when rotated credential persistence fails",async()=>{
  let used=false;
  await assert.rejects(runWithMicrosoftToken({
    clientId,clientSecret:"fixture-secret",
    credentialStore:{load:async()=>({refreshToken:"old"}),
      save:async()=>{throw Error("secure_store_down")}},
    fetchImpl:async()=>({ok:true,json:async()=>({
      access_token:"new",refresh_token:"rotated",expires_in:3600
    })}),
    run:async()=>{used=true}
  }),/secure_store_down/);
  assert.equal(used,false);
});
test("never include OAuth response body in provider errors",async()=>{
  await assert.rejects(refreshMicrosoftGraphToken({
    clientId,clientSecret:"fixture-secret",refreshToken:"fixture-refresh",
    fetchImpl:async()=>({ok:false,status:401,json:async()=>({secret:"do-not-log"})})
  }),err=>err.message==="microsoft_token_http_401");
});
