// Server-only composition for a single Outlook-to-D1 collection pass.
// No HTTP route or cron. Call only from an authorized, explicitly enabled
// runtime with a verified operator key and approved Microsoft OAuth consent.
import {runWithMicrosoftToken} from "./leboncoin-oauth.mjs";
import {verifyMicrosoftMailbox} from "./leboncoin-identity.mjs";
import {createD1OAuthStores} from "./leboncoin-oauth-store.mjs";
import {createEncryptedD1DeltaStore} from "./leboncoin-delta-store.mjs";
import {syncLeboncoinDelta} from "./leboncoin-delta.mjs";
import {withOutlookRunLease} from "./leboncoin-run-lease.mjs";

const KEY=/^[a-f0-9]{64}$/i;
export async function runOutlookLeboncoinCollection({
  env, ownerKey, fetchImpl=fetch, maxPages=10
}) {
  if(env?.OUTLOOK_INGEST_ENABLED!=="true")
    return {status:"DISABLED",active:false};
  if(!KEY.test(ownerKey || "") || !env?.DB?.prepare || !env?.DB?.batch ||
     !env.OUTLOOK_ENCRYPTION_KEY || !env.OUTLOOK_CLIENT_ID ||
     !env.OUTLOOK_CLIENT_SECRET || !env.OUTLOOK_DELTA_ENCRYPTION_KEY)
    throw new Error("outlook_runtime_not_configured");
  return withOutlookRunLease({db:env.DB,ownerKey,run:async({signal,assertActive,leaseId})=>{
  const stores=await createD1OAuthStores({
    db:env.DB,mailboxKey:ownerKey,encryptionKey:env.OUTLOOK_ENCRYPTION_KEY,
    lease:{ownerKey,leaseId}
  });
  const saved=await stores.credentialStore.load();
  if(!saved?.refreshToken || !saved?.accountId)
    throw new Error("outlook_requires_verified_consent");
  const deltaStore=await createEncryptedD1DeltaStore({
    db:env.DB,mailboxKey:ownerKey,encryptionKey:env.OUTLOOK_DELTA_ENCRYPTION_KEY,
    lease:{ownerKey,leaseId}
  });
  return runWithMicrosoftToken({
    credentialStore:stores.credentialStore,
    clientId:env.OUTLOOK_CLIENT_ID,
    clientSecret:env.OUTLOOK_CLIENT_SECRET,
    tenant:env.OUTLOOK_TENANT||"consumers",
    fetchImpl,
    run:async accessToken=>{
      await verifyMicrosoftMailbox(accessToken,{
        expectedAccountId:saved.accountId,fetchImpl
      });
      const stats=await syncLeboncoinDelta({
        token:accessToken,db:env.DB,cursorStore:deltaStore,
        fetchImpl,maxPages,signal,assertActive,lease:{ownerKey,leaseId}
      });
      return {...stats,active:true,source:"OUTLOOK_LEBONCOIN"};
    }
  });
  }});
}
