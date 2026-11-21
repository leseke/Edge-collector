import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createEncryptedD1DeltaStore} from "../src/leboncoin-delta-store.mjs";
if (!globalThis.crypto) globalThis.crypto=webcrypto;
const key="ab".repeat(32), mailbox="1234567890abcdef";
function fakeDb() {
  let record=null,conflict=false;
  return {get row(){return record},set conflict(value){conflict=value},
    prepare(sql){return {bind(...args){return {
      first:async()=>record,
      run:async()=>{
        if(conflict) return {meta:{changes:0}};
        if(sql.startsWith("INSERT")) {
          if(record) return {meta:{changes:0}};
          record={nonce_b64:args[1],ciphertext_b64:args[2],generation:1};
        } else {
          if(!record || record.generation!==args[4]) return {meta:{changes:0}};
          record={nonce_b64:args[0],ciphertext_b64:args[1],generation:record.generation+1};
        }
        return {meta:{changes:1}};
      }
    }}}}
  };
}
test("stores only AES-GCM encrypted cursor and resumes",async()=>{
  const db=fakeDb();
  const s=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:key});
  assert.equal(await s.load(),null);
  const url="https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=sensitive";
  await s.save(url);
  assert.equal(db.row.generation,1);
  assert.equal(JSON.stringify(db.row).includes("sensitive"),false);
  const reopened=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:key});
  assert.equal(await reopened.load(),url);
  await reopened.save(url+"2");
  assert.equal(db.row.generation,2);
});
test("refuses invalid key and stale concurrent writer",async()=>{
  const db=fakeDb();
  await assert.rejects(createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:"plaintext"}),/invalid_cursor_store_configuration/);
  const first=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:key});
  const other=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:key});
  await first.load();await other.load();
  await first.save("cursor1");
  await assert.rejects(other.save("cursor2"),/delta_cursor_concurrent_update/);
});
test("refuses ciphertext decryption with wrong key",async()=>{
  const db=fakeDb(),first=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:key});
  await first.load();await first.save("secret");
  const other=await createEncryptedD1DeltaStore({db,mailboxKey:mailbox,encryptionKey:"cd".repeat(32)});
  await assert.rejects(other.load(),/delta_cursor_decryption_failed/);
});
