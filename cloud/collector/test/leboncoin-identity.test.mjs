import test from "node:test";
import assert from "node:assert/strict";
import {verifyMicrosoftMailbox} from "../src/leboncoin-identity.mjs";
test("accepts authenticated Graph /me identity without persisting email",async()=>{
  let path=null;
  const result=await verifyMicrosoftMailbox("access",{fetchImpl:async(url,init)=>{
    path=url;
    assert.equal(init.headers.Authorization,"Bearer access");
    return {ok:true,json:async()=>({id:"graph-account-123",mail:"private@example.invalid"})};
  }});
  assert.equal(path,"https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName,mail");
  assert.deepEqual(result,{accountId:"graph-account-123"});
});
test("refuses account substitution",async()=>{
  await assert.rejects(verifyMicrosoftMailbox("access",{expectedAccountId:"original",fetchImpl:async()=>({ok:true,json:async()=>({id:"different"})})}),/graph_identity_mismatch/);
});
test("fails closed for missing identity or Graph errors",async()=>{
  await assert.rejects(verifyMicrosoftMailbox("access",{fetchImpl:async()=>({ok:true,json:async()=>({mail:"attacker@example.invalid"})})}),/invalid_graph_identity/);
  await assert.rejects(verifyMicrosoftMailbox("access",{fetchImpl:async()=>({ok:false,status:401})}),/graph_identity_http_401/);
});
