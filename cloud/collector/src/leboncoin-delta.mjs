// Microsoft Graph message delta: incremental read, bounded pages, replay-safe checkpoints.
// Keep cursor storage behind an injected, encrypted and tenant-scoped store.
// This module never sees OAuth refresh credentials and does not schedule itself.
import { parseLeboncoinAlert } from "./leboncoin-email.mjs";
import { persistLeboncoinAlerts } from "./leboncoin-d1.mjs";

const BASE = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta";
const FIELDS = "id,subject,receivedDateTime,body";
export function validateGraphDeltaUrl(value) {
  if (typeof value !== "string" || value.length > 8192) throw new Error("invalid_delta_cursor");
  let url;
  try { url = new URL(value); } catch { throw new Error("invalid_delta_cursor"); }
  // Keep the cursor inside the exact Inbox delta resource. The Graph nextLink
  // can include opaque skip/delta tokens and must be used without modification.
  if (url.origin !== "https://graph.microsoft.com" ||
      // Graph may return OData canonical mailfolders('ID') rather than /mailFolders/ID.
      !(
        /^\/v1\.0\/me\/mailfolders\/[^/]+\/messages\/delta$/i.test(url.pathname) ||
        /^\/v1\.0\/me\/mailfolders\('[A-Za-z0-9_+=-]{1,1024}'\)\/messages\/delta$/i.test(decodeURIComponent(url.pathname))
      ) ||
      url.username || url.password || url.hash) throw new Error("unsafe_delta_cursor");
  return url.toString();
}
function initialUrl() {
  return BASE + "?" + new URLSearchParams({"$select":FIELDS,"$top":"50"});
}
function saneStore(store) {
  if (!store || typeof store.load !== "function" || typeof store.save !== "function")
    throw new Error("missing_secure_cursor_store");
}
export async function syncLeboncoinDelta({
  token, db, cursorStore, fetchImpl = fetch, maxPages = 10,
  clock = () => new Date().toISOString()
}) {
  if (typeof token !== "string" || !token.trim()) throw new Error("missing_graph_token");
  if (!db?.prepare || !db?.batch) throw new Error("missing_d1_database");
  saneStore(cursorStore);
  if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 50) throw new Error("invalid_max_pages");

  let url = validateGraphDeltaUrl((await cursorStore.load()) || initialUrl());
  const visited = new Set();
  let pages = 0, scanned = 0, alerts = 0, extracted = 0, inserted = 0, duplicates = 0;
  while (pages < maxPages) {
    if (visited.has(url)) throw new Error("graph_delta_pagination_loop");
    visited.add(url);
    const response = await fetchImpl(url,{
      headers:{Authorization:"Bearer " + token,Accept:"application/json"},
      redirect:"error"
    });
    if (response.status === 410) {
      // Do not silently reset the cursor: it would replay a mailbox and
      // suppress important data gaps. Operator must authorize a rescan.
      throw new Error("graph_delta_token_expired");
    }
    if (!response.ok) throw new Error("graph_delta_http_" + response.status);
    const body = await response.json();
    if (!Array.isArray(body.value)) throw new Error("invalid_graph_delta_response");
    const next = body["@odata.nextLink"];
    const delta = body["@odata.deltaLink"];
    if (Boolean(next) === Boolean(delta)) throw new Error("graph_delta_missing_or_ambiguous_cursor");
    const checkpoint = validateGraphDeltaUrl(next || delta);
    const parsed = body.value
      .filter(m => m && !m["@removed"])
      .map(parseLeboncoinAlert)
      .filter(Boolean);
    // If persistence fails, cursor is NOT advanced; the next attempt replays
    // exactly the same page and the message PKs prevent duplicate observations.
    const persisted = await persistLeboncoinAlerts(db,parsed,{clock});
    await cursorStore.save(checkpoint);
    pages++;
    scanned += body.value.length;
    alerts += parsed.length;
    extracted += parsed.reduce((n,a)=>n+a.listings.length,0);
    inserted += persisted.inserted_listings;
    duplicates += persisted.already_seen_messages;
    if (delta) return {
      status: alerts ? "OK":"EMPTY", complete:true,
      pages, messages_scanned:scanned, matching_alerts:alerts,
      extracted_listing_rows:extracted, inserted_listings:inserted,
      already_seen_messages:duplicates
    };
    url = checkpoint;
  }
  return {
    status:"PARTIAL",complete:false,pages,messages_scanned:scanned,
    matching_alerts:alerts,extracted_listing_rows:extracted,
    inserted_listings:inserted,already_seen_messages:duplicates
  };
}
