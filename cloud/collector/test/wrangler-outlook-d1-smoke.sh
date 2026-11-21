#!/usr/bin/env bash
# Real Wrangler local D1 smoke test for the isolated Outlook schema.
# Runs only against the runner's local ephemeral database; no Cloudflare auth,
# remote D1 operations, Microsoft mailbox access or deployment.
set -euo pipefail
cd "$(dirname "$0")/.."
config="wrangler.ci.json"
db="edge-tcg-history-ci"
if [[ ! -f "$config" ]]; then
  echo "Missing locally generated test Wrangler config" >&2
  exit 1
fi
d1() {
  npx --no-install wrangler d1 execute "$db" --local --config "$config" --command "$1"
}
for migration in 003_leboncoin_outlook.sql 004_outlook_delta_cursor.sql 005_outlook_oauth_secure.sql 006_outlook_run_lease.sql; do
  npx --no-install wrangler d1 execute "$db" --local --config "$config" --file "migrations/$migration"
done
owner="$(printf 'a%.0s' {1..64})"
original="$(printf 'b%.0s' {1..36})"
replacement="$(printf 'c%.0s' {1..36})"
d1 "INSERT INTO lbc_sync_lease(owner_key,lease_id,expires_at_ms,acquired_at_ms) VALUES ('$owner','$original',9999999999999,1000)"
d1 "INSERT OR IGNORE INTO lbc_alert_messages(message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at) SELECT 'ci-mail','2026-11-19T00:00:00Z','Pokemon',1,1,0,'2026-11-19T00:01:00Z' WHERE EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
d1 "INSERT OR IGNORE INTO lbc_listing_observations(message_id,listing_id,observed_at,source_url,title,price_cents,currency,location,category_hint,price_kind,availability,evidence) SELECT 'ci-mail','leboncoin:3312468604','2026-11-19T00:00:00Z','https://www.leboncoin.fr/vi/3312468604.htm','Fixture',7500,'EUR',NULL,'Pokemon','LISTING','UNVERIFIED','EMAIL_EXCERPT' WHERE EXISTS (SELECT 1 FROM lbc_alert_messages WHERE message_id='ci-mail') AND EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
d1 "INSERT OR IGNORE INTO lbc_graph_delta_cursor(mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at) SELECT '$owner','nonce','encrypted',1,'2026-11-19T00:02:00Z' WHERE EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
d1 "INSERT OR IGNORE INTO lbc_oauth_credentials(mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at) SELECT '$owner','nonce','encrypted',1,'2026-11-19T00:02:00Z' WHERE EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
# Replace the lock to simulate an expired/replaced worker. All stale writes
# must be ignored by the SQLite engine itself.
d1 "UPDATE lbc_sync_lease SET lease_id='$replacement' WHERE owner_key='$owner'"
d1 "UPDATE lbc_graph_delta_cursor SET generation=generation+1 WHERE mailbox_key='$owner' AND EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
d1 "UPDATE lbc_oauth_credentials SET generation=generation+1 WHERE mailbox_key='$owner' AND EXISTS (SELECT 1 FROM lbc_sync_lease WHERE owner_key='$owner' AND lease_id='$original' AND expires_at_ms>1001)"
# Force a failure if the D1 predicates do not agree; using an impossible
# CHECK-violating row makes assertions independent of CLI table formatting.
d1 "INSERT INTO lbc_sync_lease(owner_key,lease_id,expires_at_ms,acquired_at_ms) SELECT '$owner','bad',0,0 WHERE NOT EXISTS (SELECT 1 FROM lbc_listing_observations WHERE message_id='ci-mail' AND listing_id='leboncoin:3312468604') OR (SELECT generation FROM lbc_graph_delta_cursor WHERE mailbox_key='$owner')<>1 OR (SELECT generation FROM lbc_oauth_credentials WHERE mailbox_key='$owner')<>1"
echo "EDGE_OUTLOOK_LOCAL_D1_SMOKE_PASS"
