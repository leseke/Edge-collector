// Additive immutable D1 writer for parsed saved-search alerts.
// The caller is responsible for obtaining Graph consent and scheduling.
// Each batch is one atomic D1 transaction; failures leave no half-written email.
const VALID_ID = /^leboncoin:\d+$/;
const VALID_TIME = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/;

export function validateAlert(alert) {
  if (!alert || typeof alert.message_id !== "string" || !alert.message_id ||
      alert.message_id.length > 1024 || !VALID_TIME.test(alert.received_at || "") ||
      typeof alert.search !== "string" || !alert.search.trim() || alert.search.length > 200 ||
      !Number.isSafeInteger(alert.advertised_count) || alert.advertised_count < 0 ||
      !Array.isArray(alert.listings) || alert.listings.length > 100 ||
      alert.listings.length > alert.advertised_count && alert.advertised_count !== 0) {
    throw new Error("invalid_lbc_alert");
  }
  const ids = new Set();
  for (const item of alert.listings) {
    if (!VALID_ID.test(item.id || "") || ids.has(item.id) ||
        item.source_url !== "https://www.leboncoin.fr/vi/" + item.id.slice(10) + ".htm" ||
        item.price_kind !== "LISTING" || item.availability !== "UNVERIFIED" ||
        item.evidence !== "EMAIL_EXCERPT" ||
        item.observed_at !== alert.received_at ||
        (item.price_cents !== null && (!Number.isSafeInteger(item.price_cents) || item.price_cents < 0)) ||
        (item.currency !== null && item.currency !== "EUR") ||
        (item.title !== null && (typeof item.title !== "string" || item.title.length > 500)) ||
        (item.location !== null && (typeof item.location !== "string" || item.location.length > 300))) {
      throw new Error("invalid_lbc_listing");
    }
    ids.add(item.id);
  }
  return alert;
}

export async function persistLeboncoinAlerts(db, alerts, { clock = () => new Date().toISOString(), lease = null } = {}) {
  if (!db || typeof db.prepare !== "function" || typeof db.batch !== "function") throw new Error("invalid_d1_database");
  if (!Array.isArray(alerts) || alerts.length > 500) throw new Error("invalid_lbc_batch");
  if (lease !== null && (!/^[a-f0-9]{64}$/i.test(lease.ownerKey || "") ||
      !/^[a-f0-9-]{36}$/i.test(lease.leaseId || "")))
    throw new Error("invalid_lbc_lease");
  let insertedMessages = 0, insertedListings = 0, skippedMessages = 0;
  for (const untrusted of alerts) {
    const alert = validateAlert(untrusted);
    const exists = await db.prepare("SELECT 1 AS seen FROM lbc_alert_messages WHERE message_id = ? LIMIT 1")
      .bind(alert.message_id).first();
    if (exists) {
      // A legacy or corrupt partially-written email must NOT be treated
      // as a safe duplicate: advancing the Graph cursor would lose data.
      // The append-only ledger cannot be repaired by updating its rows.
      const integrity=await db.prepare(`SELECT m.extracted_count AS expected_count,
        (SELECT COUNT(*) FROM lbc_listing_observations o
         WHERE o.message_id = m.message_id) AS actual_count
        FROM lbc_alert_messages m WHERE m.message_id = ? LIMIT 1`)
        .bind(alert.message_id).first();
      if(!integrity || !Number.isSafeInteger(integrity.expected_count) ||
         !Number.isSafeInteger(integrity.actual_count) ||
         integrity.expected_count!==integrity.actual_count ||
         integrity.expected_count!==alert.listings.length)
        throw new Error("outlook_existing_message_incomplete_or_changed");
      skippedMessages++;
      continue;
    }
    const now = clock();
    if (!VALID_TIME.test(now)) throw new Error("invalid_clock");
    const fence = lease ? `EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key = ? AND lease_id = ? AND expires_at_ms > ?)` : null;
    const leaseArgs = lease ? [lease.ownerKey,lease.leaseId,Date.now()] : [];
    const statements = [
      db.prepare(`INSERT OR IGNORE INTO lbc_alert_messages
        (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
        ${fence ? `SELECT ?,?,?,?,?,?,? WHERE ${fence}` : "VALUES (?,?,?,?,?,?,?)"}`).bind(alert.message_id,alert.received_at,alert.search,
          alert.advertised_count,alert.listings.length,Number(Boolean(alert.truncated_email)),now,...leaseArgs)
    ];
    for (const item of alert.listings) {
      statements.push(db.prepare(`INSERT OR IGNORE INTO lbc_listing_observations
        (message_id,listing_id,observed_at,source_url,title,price_cents,currency,location,category_hint,price_kind,availability,evidence)
        SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS
        (SELECT 1 FROM lbc_alert_messages WHERE message_id = ? AND ingested_at = ?)${fence ? ` AND ${fence}` : ""}`)
        .bind(alert.message_id,item.id,item.observed_at,item.source_url,item.title,
          item.price_cents,item.currency,item.location,alert.search,
          "LISTING","UNVERIFIED","EMAIL_EXCERPT",alert.message_id,now,...leaseArgs));
    }
    // D1 batch is a single SQLite transaction. Make partial insertion a
    // database-level error so the entire batch rolls back BEFORE the Graph
    // cursor can advance. The deliberately invalid advertised_count=-1
    // triggers the immutable alert table's CHECK constraint only when the
    // message or one of its expected listing rows is absent.
    // Do not "recover" by updating immutable observations.
    statements.push(db.prepare(`INSERT INTO lbc_alert_messages
      (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
      SELECT ?,?,?,-1,0,0,? WHERE
      NOT EXISTS (SELECT 1 FROM lbc_alert_messages WHERE message_id=? AND ingested_at=?)
      OR (SELECT COUNT(*) FROM lbc_listing_observations WHERE message_id=?)<>?`)
      .bind(alert.message_id,alert.received_at,alert.search,now,
        alert.message_id,now,alert.message_id,alert.listings.length));
    const results = await db.batch(statements);
    if (results[0]?.meta?.changes === 1) {
      // Last statement is the SQL integrity assertion, not an observation.
      const insertedRows=results.slice(1,-1).reduce((sum,result)=>
        sum + (result?.meta?.changes===1 ? 1 : 0),0);
      if(results.length!==alert.listings.length+2 ||
         insertedRows!==alert.listings.length ||
         results.at(-1)?.meta?.changes!==0)
        throw new Error("outlook_observation_batch_integrity_unknown");
      insertedMessages++;
      insertedListings+=insertedRows;
    } else if (lease) throw new Error("outlook_observation_lease_lost_or_conflict");
    else skippedMessages++;
  }
  return {inserted_messages:insertedMessages, inserted_listings:insertedListings,
    already_seen_messages:skippedMessages};
}
