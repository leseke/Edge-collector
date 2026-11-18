import { reviewedCardLiquidity } from "./card-liquidity";
import { compareMarketWindows, type TrendSale } from "./market-trends";

type PaidSaleRow = { variant_key: string; lot_id: string; sold_day: string; price_cents: number; source_url: string };
type Scan = { scan_day: string; status: "RUNNING" | "OK" | "EMPTY" | "PARTIAL" | "FAILED" };
type Lead = { source_url: string; category: string; kind: string; first_seen_day: string };
const fallback = { cards: reviewedCardLiquidity, scan: null, leads: [] as Lead[], trends: [] as ReturnType<typeof compareMarketWindows> };
type PaidSaleDatabase = {
  prepare(query: string): {
    bind(...values: string[]): { all<T>(): Promise<{ results: T[] }> };
  };
};

export async function getRadarPaidSales() {
  try {
    const { getCloudflareContext } = await import("@opennextjs/cloudflare");
    const { env } = await getCloudflareContext({ async: true });
    const db = (env as { SALES_DB?: PaidSaleDatabase }).SALES_DB;
    if (!db) return fallback;
    return await readRadarPaidSales(db);
  } catch {
    return fallback;
  }
}

export async function readRadarPaidSales(db: PaidSaleDatabase, asOf = new Date()) {
    const today = asOf.toISOString().slice(0, 10);
    const oldest = new Date(+asOf - 365 * 86_400_000).toISOString().slice(0, 10);
    const scan = await db.prepare("SELECT scan_day,status FROM paid_sale_scans WHERE scan_day<=? ORDER BY scan_day DESC LIMIT 1")
      .bind(today).all<Scan>();
    const cards = await Promise.all(reviewedCardLiquidity.map(async card => {
      const { results } = await db.prepare(`SELECT variant_key,lot_id,sold_day,price_cents,source_url FROM paid_market_sales
        WHERE variant_key=? AND sold_day BETWEEN ? AND ? ORDER BY sold_day DESC,lot_id LIMIT 200`)
        .bind(card.key, oldest, today).all<PaidSaleRow>();
      const sales = new Map(card.paidSales.map(sale => [sale.id, sale]));
      for (const row of results) {
        if (row.variant_key !== card.key || sales.has(row.lot_id)) continue;
        const id = row.lot_id.match(/^gcc-([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$/);
        const source = id && "https://gradedcardcenter.com/item/" + id[1];
        if (!source || row.source_url !== source || !Number.isSafeInteger(row.price_cents) || row.price_cents <= 0) continue;
        sales.set(row.lot_id, { id: row.lot_id, day: row.sold_day, cents: row.price_cents, source });
      }
      return { ...card, paidSales: [...sales.values()] };
    }));
    const windowStart = new Date(+asOf - 59 * 86_400_000).toISOString().slice(0, 10);
    const [markets, leads] = await Promise.all([
      db.prepare(`SELECT variant_key,sold_day,price_cents FROM paid_market_sales
        WHERE sold_day BETWEEN ? AND ? ORDER BY sold_day DESC,lot_id LIMIT 1001`).bind(windowStart, today).all<TrendSale>(),
      db.prepare(`SELECT source_url,category,kind,first_seen_day FROM market_discovery_leads
        WHERE first_seen_day BETWEEN ? AND ? AND kind<>'LOT'
        ORDER BY first_seen_day DESC,source_url LIMIT 12`).bind(windowStart, today).all<Lead>(),
    ]);
    const trends = markets.results.length <= 1000 ? compareMarketWindows(markets.results, today) : [];
    return { cards, scan: scan.results[0] ?? null, leads: leads.results, trends };
}
