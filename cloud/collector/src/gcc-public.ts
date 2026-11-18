import { readBoundedText } from "./bounded.mjs";
import { readPaidLot, type PaidSaleEnv } from "./paid-sales";

const site = "https://gradedcardcenter.com";
export const publicAuctionPage = site + "/filtres/auctions";
const lotPrefix = site + "/item/";
const dayMs = 86_400_000;

export function publicLotIds(html: string): string[] {
  const ids = new Set<string>();
  const anchors = /<a\b[^>]*\bhref=["'](?:https:\/\/gradedcardcenter\.com)?\/item\/([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})["']/gi;
  for (const match of html.matchAll(anchors)) ids.add(match[1].toLowerCase());
  return [...ids];
}

async function fetchHtml(url: string, request: typeof fetch) {
  const response = await request(url, {
    redirect: "error", signal: AbortSignal.timeout(8_000), headers: { Accept: "text/html", "Accept-Language": "fr" },
  });
  if (!response.ok || !response.headers.get("content-type")?.includes("text/html")) throw new Error("gcc_unavailable");
  return readBoundedText(response, 1_500_000);
}

export async function collectPublicGccLots(env: Pick<PaidSaleEnv, "DB">, scheduledTime: number, request: typeof fetch = fetch) {
  const day = new Date(scheduledTime).toISOString().slice(0, 10);
  const claim = await env.DB.prepare("INSERT INTO paid_sale_scans(scan_day,status) VALUES (?,'RUNNING') ON CONFLICT(scan_day) DO NOTHING").bind(day).run();
  if (!claim.meta.changes) return;

  let failures = 0, checked = 0, verified = 0, inserted = 0;
  try {
    const ids = publicLotIds(await fetchHtml(publicAuctionPage, request));
    if (!ids.length) failures++;
    else {
      const offset = Math.floor(scheduledTime / dayMs) % ids.length;
      const sample = [...ids.slice(offset), ...ids.slice(0, offset)].slice(0, 4);
      for (const id of sample) {
        await env.DB.prepare("INSERT INTO gcc_lot_queue(lot_id,first_seen_day,next_check_day) VALUES (?,?,?) ON CONFLICT(lot_id) DO NOTHING").bind(id, day, day).run();
      }
    }
  } catch {
    failures++;
  }

  const oldest = new Date(scheduledTime - 28 * dayMs).toISOString().slice(0, 10);
  const tomorrow = new Date(scheduledTime + dayMs).toISOString().slice(0, 10);
  try {
    const { results } = await env.DB.prepare(`SELECT lot_id FROM gcc_lot_queue
      WHERE next_check_day <= ? AND first_seen_day >= ? AND paid_day IS NULL
      ORDER BY next_check_day,first_seen_day DESC,lot_id LIMIT 6`).bind(day, oldest).all<{lot_id: string}>();
    for (const { lot_id: id } of results) {
      checked++;
      let paidDay: string | null = null;
      try {
        const html = await fetchHtml(lotPrefix + id, request);
        const sale = readPaidLot(html, id, day);
        if (sale) {
          const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(html));
          const hash = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
          const row = await env.DB.prepare(`INSERT INTO paid_market_sales
            (lot_id,variant_key,sold_day,price_cents,source_url,collected_at,payload_sha256)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(lot_id) DO NOTHING`)
            .bind("gcc-" + id, sale.key, sale.day, sale.cents, sale.source, new Date().toISOString(), hash).run();
          inserted += row.meta.changes ?? 0;
          verified++;
          paidDay = sale.day;
        }
      } catch {
        failures++;
      }
      await env.DB.prepare("UPDATE gcc_lot_queue SET next_check_day=?,paid_day=? WHERE lot_id=?")
        .bind(tomorrow, paidDay, id).run();
    }
  } catch {
    failures++;
  }

  const status = failures > 0 ? (verified > 0 || checked > failures ? "PARTIAL" : "FAILED") :
    verified > 0 ? "OK" : "EMPTY";
  await env.DB.prepare("UPDATE paid_sale_scans SET status=?,checked=?,verified=?,inserted=? WHERE scan_day=?")
    .bind(status, checked, verified, inserted, day).run();
}
