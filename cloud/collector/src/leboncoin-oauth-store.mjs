// Microsoft Outlook OAuth secrets, encrypted at rest via WebCrypto AES-256-GCM.
// D1 stores ciphertext only. No OAuth callback/HTTP endpoint is exposed here.
const encoder=new TextEncoder(),decoder=new TextDecoder();
const encode=bytes=>btoa(String.fromCharCode(...bytes));
const decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const MAILBOX=/^[a-f0-9]{16,128}$/i;
const STATE=/^[A-Za-z0-9_-]{40,64}$/;
async function importKey(hex) {
  if(typeof hex!=="string" || !/^[0-9a-f]{64}$/i.test(hex))
    throw new Error("invalid_oauth_encryption_key");
  return crypto.subtle.importKey("raw",
    Uint8Array.from(hex.match(/../g),v=>parseInt(v,16)),"AES-GCM",false,["encrypt","decrypt"]);
}
async function seal(key,domain,data) {
  const nonce=crypto.getRandomValues(new Uint8Array(12));
  const ciphertext=new Uint8Array(await crypto.subtle.encrypt({
    name:"AES-GCM",iv:nonce,additionalData:encoder.encode(domain)
  },key,encoder.encode(JSON.stringify(data))));
  return {nonce_b64:encode(nonce),ciphertext_b64:encode(ciphertext)};
}
async function unseal(key,domain,row) {
  try {
    const bytes=await crypto.subtle.decrypt({name:"AES-GCM",
      iv:decode(row.nonce_b64),additionalData:encoder.encode(domain)
    },key,decode(row.ciphertext_b64));
    return JSON.parse(decoder.decode(bytes));
  } catch {throw new Error("oauth_secret_decryption_failed")}
}
export async function createD1OAuthStores({db,mailboxKey,encryptionKey,clock=()=>new Date().toISOString()}) {
  if(!db?.prepare || !MAILBOX.test(mailboxKey || ""))throw new Error("invalid_oauth_store_config");
  const key=await importKey(encryptionKey);
  let generation=null;
  const secretDomain="EDGE:outlook-oauth-credentials:"+mailboxKey;
  return {
    pendingStore:{
      async create(entry) {
        if(!entry || !STATE.test(entry.stateHash || "") ||
          typeof entry.sessionHash!=="string" || !STATE.test(entry.sessionHash) ||
          typeof entry.verifier!=="string" || entry.verifier.length<43 ||
          typeof entry.redirectUri!=="string" || !Number.isSafeInteger(entry.expiresAt))
          throw new Error("invalid_oauth_pending_entry");
        const {nonce_b64,ciphertext_b64}=await seal(key,
          "EDGE:outlook-oauth-pending:"+mailboxKey+":"+entry.stateHash,entry);
        // Unique stateHash: reusing a nonce/state cannot overwrite a pending consent.
        await db.prepare(`INSERT INTO lbc_oauth_pending
          (state_hash,nonce_b64,ciphertext_b64,expires_at,created_at)
          VALUES (?,?,?,?,?)`)
          .bind(entry.stateHash,nonce_b64,ciphertext_b64,entry.expiresAt,clock()).run();
      },
      async consume(stateHash) {
        if(!STATE.test(stateHash || ""))throw new Error("invalid_oauth_state_hash");
        // DELETE RETURNING is atomic in SQLite/D1: concurrent callback cannot
        // redeem a state twice, including after a failed token exchange.
        const row=await db.prepare(`DELETE FROM lbc_oauth_pending
          WHERE state_hash = ? RETURNING nonce_b64,ciphertext_b64,expires_at`)
          .bind(stateHash).first();
        if(!row)return null;
        const pending=await unseal(key,
          "EDGE:outlook-oauth-pending:"+mailboxKey+":"+stateHash,row);
        if(pending.stateHash!==stateHash)throw new Error("oauth_state_mismatch");
        return pending;
      }
    },
    credentialStore:{
      async load(){
        const row=await db.prepare(`SELECT nonce_b64,ciphertext_b64,generation
          FROM lbc_oauth_credentials WHERE mailbox_key = ?`).bind(mailboxKey).first();
        if(!row){generation=0;return null}
        const value=await unseal(key,secretDomain,row);
        if(typeof value.refreshToken!=="string" || !value.refreshToken)
          throw new Error("invalid_stored_refresh_token");
        generation=row.generation;
        return value;
      },
      async save(value){
        if(typeof value?.refreshToken!=="string" || !value.refreshToken)
          throw new Error("invalid_refresh_token");
        if(generation===null) await this.load();
        const {nonce_b64,ciphertext_b64}=await seal(key,secretDomain,
          {refreshToken:value.refreshToken});
        let stmt;
        if(generation===0){
          stmt=db.prepare(`INSERT OR IGNORE INTO lbc_oauth_credentials
            (mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at)
            VALUES (?,?,?,1,?)`).bind(mailboxKey,nonce_b64,ciphertext_b64,clock());
        } else {
          stmt=db.prepare(`UPDATE lbc_oauth_credentials SET nonce_b64=?,ciphertext_b64=?,
            generation=generation+1,modified_at=?
            WHERE mailbox_key=? AND generation=?`)
            .bind(nonce_b64,ciphertext_b64,clock(),mailboxKey,generation);
        }
        const result=await stmt.run();
        if(result?.meta?.changes!==1)throw new Error("oauth_credential_concurrent_update");
        generation++;
      }
    }
  };
}
