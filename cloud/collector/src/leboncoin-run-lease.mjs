// Single-owner D1 lease: avoid concurrent OAuth refresh/cursor mutation.
// This only protects runs within a bounded lease window; caller must ensure
// max execution duration < leaseMs and must not run past lease expiry.
const OWNER=/^[a-f0-9]{64}$/i;
export async function withOutlookRunLease({db,ownerKey,run,clock=()=>Date.now(),leaseMs=120000}) {
  if (!db?.prepare || !OWNER.test(ownerKey || "") || typeof run!=="function" ||
      !Number.isSafeInteger(leaseMs) || leaseMs<1000 || leaseMs>300000)
    throw new Error("invalid_outlook_lease_config");
  const now=clock(),leaseId=crypto.randomUUID();
  if (!Number.isSafeInteger(now) || now<0) throw new Error("invalid_clock");
  const expiry=now+leaseMs;
  // SQLite's single-statement UPSERT serializes competing lock acquisition.
  // A live lease cannot be replaced; expiry and exact owner are required.
  const result=await db.prepare(`INSERT INTO lbc_sync_lease
    (owner_key,lease_id,expires_at_ms,acquired_at_ms) VALUES (?,?,?,?)
    ON CONFLICT(owner_key) DO UPDATE SET
      lease_id=excluded.lease_id,expires_at_ms=excluded.expires_at_ms,
      acquired_at_ms=excluded.acquired_at_ms
    WHERE lbc_sync_lease.expires_at_ms <= excluded.acquired_at_ms`)
    .bind(ownerKey,leaseId,expiry,now).run();
  if (result?.meta?.changes!==1) return {status:"BUSY",active:false};
  try {
    const output=await run();
    // Detect expired lease before reporting success; another worker could have
    // reclaimed it and produced an overlapping (though idempotent) observation.
    if (clock()>=expiry) throw new Error("outlook_run_lease_expired");
    return output;
  } finally {
    await db.prepare("DELETE FROM lbc_sync_lease WHERE owner_key=? AND lease_id=?")
      .bind(ownerKey,leaseId).run();
  }
}
