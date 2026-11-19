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

export async function persistLeboncoinAlerts(db, alerts, { clock = () => new Date().toISOString() } = {}) {
  if (!db || typeof db.prepare !== "function" || typeof db.batch !== "function") throw new Error("invalid_d1_database");
  if (!Array.isArray(alerts) || alerts.length > 500) throw new Error("invalid_lbc_batch");
  let insertedMessages = 0, insertedListings = 0, skippedMessages = 0;
  for (const untrusted of alerts) {
    const alert = validateAlert(untrusted);
    const exists = await db.prepare("SELECT 1 AS seen FROM lbc_alert_messages WHERE message_id = ? LIMIT 1")
      .bind(alert.message_id).first();
    if (exists) { skippedMessages++; continue; }
    const now = clock();
    if (!VALID_TIME.test(now)) throw new Error("invalid_clock");
    const statements = [
      db.prepare(`INSERT OR IGNORE INTO lbc_alert_messages
        (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
        VALUES (?,?,?,?,?,?,?)`).bind(alert.message_id,alert.received_at,alert.search,
          alert.advertised_count,alert.listings.length,Number(Boolean(alert.truncated_email)),now)
    ];
    for (const item of alert.listings) {
      statements.push(db.prepare(`INSERT OR IGNORE INTO lbc_listing_observations
        (message_id,listing_id,observed_at,source_url,title,price_cents,currency,location,category_hint,price_kind,availability,evidence)
        SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS
        (SELECT 1 FROM lbc_alert_messages WHERE message_id = ? AND ingested_at = ?)`)
        .bind(alert.message_id,item.id,item.observed_at,item.source_url,item.title,
          item.price_cents,item.currency,item.location,alert.search,
          "LISTING","UNVERIFIED","EMAIL_EXCERPT",alert.message_id,now));
    }
    const results = await db.batch(statements);
    if (results[0]?.meta?.changes === 1) {
      insertedMessages++;
      insertedListings += results.slice(1).reduce((sum,result) => sum + (result.meta?.changes || 0),0);
    } else skippedMessages++;
  }
  return {inserted_messages:insertedMessages, inserted_listings:insertedListings,
    already_seen_messages:skippedMessages};
}
