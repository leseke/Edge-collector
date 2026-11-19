// Compose bounded Graph read and append-only D1 persistence.
// Explicit invocation only: not wired to Worker fetch/scheduled handlers.
import { collectGraphAlerts } from "./leboncoin-email.mjs";
import { persistLeboncoinAlerts } from "./leboncoin-d1.mjs";

export async function syncOutlookLeboncoin({ token, db, fetchImpl = fetch, maxPages = 10,
  pageSize = 50, clock = () => new Date().toISOString() }) {
  // Never accept a simulated user authorization as an OAuth token.
  if (typeof token !== "string" || token.trim().length === 0) throw new Error("missing_graph_token");
  if (!db?.prepare || !db?.batch) throw new Error("missing_d1_database");
  const result = await collectGraphAlerts({token,fetchImpl,maxPages,pageSize});
  // Safe partial commitment: successfully fetched pages can be ingested,
  // but PARTIAL must remain visible because deeper mailbox pages were not scanned.
  const saved = await persistLeboncoinAlerts(db,result.alerts,{clock});
  return {
    status:result.status,
    messages_scanned:result.scanned,
    saved_search_alerts:result.alerts.length,
    advertised_results_sum:result.alerts.reduce((sum,x)=>sum+x.advertised_count,0),
    extracted_listing_rows:result.alerts.reduce((sum,x)=>sum+x.extracted_count,0),
    unique_listing_ids:result.listings.length,
    ...saved,
    remaining_pages_possible:result.remaining_pages_possible,
    // Never expose raw mailbox emails or OAuth credentials in operational stats.
  };
}
