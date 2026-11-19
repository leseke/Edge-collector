// EDGE Leboncoin email ingestion. Mail summaries are LISTINGS, never completed sales.
// Pure parser: no network access, credentials, or personal message retention.
const AD = /https:\/\/www\.leboncoin\.fr\/vi\/(\d+)\.htm/i;
const euro = /(?:^|\s)(\d[\d\s]*(?:[,.]\d{1,2})?)\s*€/;
const removeImages = (s) => s.replace(/!\[[^\]]*\]\([^)]*\)/gs, " ");
const clean = (s) => removeImages(s).replace(/\s+/g, " ").trim();

export function parseLeboncoinAlert(message) {
  const subject = String(message.subject || "");
  const match = subject.match(/^(.+?)\s*:\s*([\d\s]+)\s+nouveaux? résultats?/i);
  if (!match) return null;
  const category = match[1].trim();
  const advertisedCount = Number(match[2].replace(/\s/g, ""));
  const body = String(message.body?.content || message.bodyPreview || "");
  // Microsoft Graph can return Markdown-converted HTML with wrapped URLs.
  // Link suffixes are tracking parameters, deliberately excluded.
  const source = body.replace(/\r/g, "").replace(/\n(?=[\w-]+(?:\/[\w-]+)*[.)#&=?-])/g, "");
  const links = /\|\s*\[\s*((?:(?!\|\s*\[)[\s\S])*?)\]\((https:\/\/www\.leboncoin\.fr\/vi\/\d+\.htm)[^)]*\)/g;
  const seen = new Set(), listings = [];
  for (const m of source.matchAll(links)) {
    const id = m[2].match(AD)?.[1];
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const label = clean(m[1]);
    const price = label.match(euro);
    const priceCents = price ? Math.round(Number(price[1].replace(/\s/g, "").replace(",", ".")) * 100) : null;
    const title = price ? label.slice(0, price.index).trim() : label;
    const location = price ? label.slice(price.index + price[0].length).trim() : "";
    listings.push({
      id: "leboncoin:" + id,
      source: "leboncoin_email",
      source_url: "https://www.leboncoin.fr/vi/" + id + ".htm",
      title: title || null,
      price_cents: Number.isFinite(priceCents) ? priceCents : null,
      currency: price ? "EUR" : null,
      location: location || null,
      price_kind: "LISTING",
      availability: "UNVERIFIED",
      category_hint: category,
      evidence: "EMAIL_EXCERPT",
      observed_at: message.receivedDateTime || null
    });
  }
  return {
    message_id: message.id || null,
    received_at: message.receivedDateTime || null,
    search: category,
    advertised_count: advertisedCount,
    extracted_count: listings.length,
    truncated_email: advertisedCount > listings.length,
    listings
  };
}

export function combineAlerts(alerts) {
  const byId = new Map();
  for (const alert of alerts) {
    if (!alert) continue;
    for (const listing of alert.listings) {
      const prior = byId.get(listing.id);
      if (prior) {
        prior.searches = [...new Set([...prior.searches, alert.search])];
      } else {
        byId.set(listing.id, { ...listing, searches: [alert.search] });
      }
    }
  }
  return [...byId.values()];
}

export async function collectGraphAlerts({ token, fetchImpl = fetch, maxPages = 10, pageSize = 50 }) {
  if (!token) throw new Error("missing_graph_token");
  if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 50) throw new Error("invalid_max_pages");
  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) throw new Error("invalid_page_size");
  let url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?"
    + new URLSearchParams({
      "$select": "id,subject,receivedDateTime,body",
      "$orderby": "receivedDateTime desc",
      "$top": String(pageSize)
    });
  const alerts = [], visited = new Set();
  let scanned = 0, pages = 0;
  while (url && pages < maxPages) {
    const u = new URL(url);
    if (u.origin !== "https://graph.microsoft.com" || !u.pathname.startsWith("/v1.0/me/")) {
      throw new Error("unsafe_graph_pagination_url");
    }
    if (visited.has(url)) throw new Error("graph_pagination_loop");
    visited.add(url);
    const response = await fetchImpl(url, { headers: { Authorization: "Bearer " + token, Accept: "application/json" } });
    if (!response.ok) throw new Error("graph_http_" + response.status);
    const body = await response.json();
    if (!Array.isArray(body.value)) throw new Error("invalid_graph_response");
    pages += 1;
    for (const message of body.value) {
      scanned++;
      const alert = parseLeboncoinAlert(message);
      if (alert) alerts.push(alert);
    }
    url = body["@odata.nextLink"] || null;
  }
  return { status: url ? "PARTIAL" : alerts.length ? "OK" : "EMPTY", scanned, pages,
    alerts, listings: combineAlerts(alerts), remaining_pages_possible: Boolean(url) };
}
