import { reviewedCardLiquidity, type Sale } from "./card-liquidity";
import { compareMarketWindows } from "./market-trends";

type PaidSaleRow = { variant_key: string; lot_id: string; sold_day: string; price_cents: number; source_url: string };
type Scan = { scan_day: string; status: "RUNNING" | "OK" | "EMPTY" | "PARTIAL" | "FAILED" };
type Lead = { source_url: string; category: string; kind: string; first_seen_day: string };
export type SaleVariant = { key: string; name: string; variant: string; paidSales: Sale[] };

const fallback = {
  cards: reviewedCardLiquidity, variants: reviewedCardLiquidity as SaleVariant[],
  recentSales: [] as (Sale & Pick<SaleVariant, "name" | "variant">)[],
  scan: null, leads: [] as Lead[], trends: [] as ReturnType<typeof compareMarketWindows>,
};

function publicPaidSale(row: PaidSaleRow): Sale | null {
  const id = row.lot_id.match(/^gcc-([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$/);
  const source = id && "https://gradedcardcenter.com/item/" + id[1];
  if (!source || row.source_url !== source || !Number.isSafeInteger(row.price_cents) || row.price_cents <= 0) return null;
  return { id: row.lot_id, day: row.sold_day, cents: row.price_cents, source };
}

function describeVariant(key: string) {
  const parts = key.split(":");
  const display = (value: string) => value.replaceAll("-", " ").replace(/^./, first => first.toUpperCase());
  const edition = (value: string) => value === "first-edition" ? "1re édition" : value === "unlimited" ? "Unlimited" : display(value);
  if (parts.length === 9 && parts[0] === "carte") {
    const [, , set, number, name, lang, printing, grader, score] = parts;
    return { name: display(name) + " " + number, variant: [display(set), lang.toUpperCase(), edition(printing), grader.toUpperCase() + " " + score].join(" · ") };
  }
  if (parts.length === 7 && ["booster", "coffret"].includes(parts[0]) && parts[6] === "scelle") {
    const [, , set, name, lang, printing] = parts;
    return { name: display(name), variant: [display(set), lang.toUpperCase(), edition(printing), "Scellé"].join(" · ") };
  }
  return null;
}
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
        const sale = publicPaidSale(row);
        if (sale) sales.set(sale.id, sale);
      }
      return { ...card, paidSales: [...sales.values()] };
    }));
    const windowStart = new Date(+asOf - 59 * 86_400_000).toISOString().slice(0, 10);
    const historyStart = new Date(+asOf - 359 * 86_400_000).toISOString().slice(0, 10);
    const [markets, leads] = await Promise.all([
      db.prepare(`SELECT variant_key,lot_id,sold_day,price_cents,source_url FROM paid_market_sales
        WHERE sold_day BETWEEN ? AND ? ORDER BY sold_day DESC,lot_id LIMIT 4001`).bind(historyStart, today).all<PaidSaleRow>(),
      db.prepare(`SELECT source_url,category,kind,first_seen_day FROM market_discovery_leads
        WHERE first_seen_day BETWEEN ? AND ? AND kind<>'LOT'
        ORDER BY first_seen_day DESC,source_url LIMIT 12`).bind(windowStart, today).all<Lead>(),
    ]);
    const variants = new Map<string, SaleVariant>(cards.map(card => [card.key, card]));
    const eligibleRows = [];
    const recentSales: typeof fallback.recentSales = [];
    for (const row of markets.results) {
      const sale = publicPaidSale(row);
      if (!sale) continue;
      let variant = variants.get(row.variant_key);
      if (!variant) {
        const description = describeVariant(row.variant_key);
        if (!description) continue;
        variant = { key: row.variant_key, ...description, paidSales: [] };
        variants.set(row.variant_key, variant);
      }
      if (!variant.paidSales.some(item => item.id === sale.id)) variant.paidSales.push(sale);
      if (recentSales.length < 8) recentSales.push({ ...sale, name: variant.name, variant: variant.variant });
      eligibleRows.push(row);
    }
    const trends = markets.results.length <= 4000 ? compareMarketWindows(eligibleRows, today) : [];
    return { cards, variants: [...variants.values()], recentSales, scan: scan.results[0] ?? null, leads: leads.results, trends };
}
