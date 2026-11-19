// Encrypted D1 implementation for Graph delta cursorStore.load/save.
// Secrets and mailbox identifiers must come from server-only bindings.
const enc = new TextEncoder();
const dec = new TextDecoder();
const b64 = bytes => btoa(String.fromCharCode(...bytes));
const unb64 = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
const ID = /^[a-f0-9]{16,128}$/i;

export async function createEncryptedD1DeltaStore({db,mailboxKey,encryptionKey,clock=()=>new Date().toISOString()}) {
  if (!db?.prepare || !ID.test(mailboxKey || "") ||
      typeof encryptionKey !== "string" || !/^[a-f0-9]{64}$/i.test(encryptionKey))
    throw new Error("invalid_cursor_store_configuration");
  const bytes = Uint8Array.from(encryptionKey.match(/../g),s=>parseInt(s,16));
  const key = await crypto.subtle.importKey("raw",bytes,"AES-GCM",false,["encrypt","decrypt"]);
  let generation = null;
  let loaded = false;
  const aad=enc.encode("EDGE:outlook-delta:"+mailboxKey);
  return {
    async load() {
      const row=await db.prepare("SELECT nonce_b64,ciphertext_b64,generation FROM lbc_graph_delta_cursor WHERE mailbox_key = ?")
        .bind(mailboxKey).first();
      loaded=true;
      if (!row) { generation=0; return null; }
      generation=row.generation;
      try {
        const decrypted=await crypto.subtle.decrypt({name:"AES-GCM",iv:unb64(row.nonce_b64),additionalData:aad},key,unb64(row.ciphertext_b64));
        return dec.decode(decrypted);
      } catch {throw new Error("delta_cursor_decryption_failed")}
    },
    async save(cursor) {
      if (!loaded) throw new Error("delta_cursor_must_load_first");
      if (typeof cursor!=="string" || cursor.length===0 || cursor.length>8192)
        throw new Error("invalid_delta_cursor");
      const nonce=crypto.getRandomValues(new Uint8Array(12));
      const encrypted=new Uint8Array(await crypto.subtle.encrypt({
        name:"AES-GCM",iv:nonce,additionalData:aad
      },key,enc.encode(cursor)));
      const now=clock();
      const sql=generation===0
        ? "INSERT OR IGNORE INTO lbc_graph_delta_cursor (mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at) VALUES (?,?,?,1,?)"
        : "UPDATE lbc_graph_delta_cursor SET nonce_b64=?,ciphertext_b64=?,generation=generation+1,modified_at=? WHERE mailbox_key=? AND generation=?";
      const stmt=generation===0
        ? db.prepare(sql).bind(mailboxKey,b64(nonce),b64(encrypted),now)
        : db.prepare(sql).bind(b64(nonce),b64(encrypted),now,mailboxKey,generation);
      const result=await stmt.run();
      if (result?.meta?.changes !== 1) throw new Error("delta_cursor_concurrent_update");
      generation++;
    }
  };
}
