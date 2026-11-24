type PriceRow = { lot_id: string; title: string; variant_key: string | null; observed_at: string; price_cents: number; previous_at: string; previous_cents: number };
type Database = { prepare(sql: string): { bind(...args: string[]): { all<T>(): Promise<{results:T[]}> } } };

// Only consecutive, positive fixed-price observations of the same lot qualify.
// Unknown identity is allowed as a weak listing signal, not a valuation.
export const priceDropQuery = `
WITH recent AS (
 SELECT lot_id,title,variant_key,observed_at,price_cents,cycle,page,
  LAG(price_cents) OVER w AS previous_cents,
  LAG(observed_at) OVER w AS previous_at,
  LAG(variant_key) OVER w AS previous_variant,
  ROW_NUMBER() OVER (PARTITION BY lot_id ORDER BY observed_at DESC,cycle DESC,page DESC) AS latest
 FROM gcc_offer_observations
 WHERE kind='fixed' AND observed_at BETWEEN ? AND ?
 WINDOW w AS (PARTITION BY lot_id ORDER BY observed_at,cycle,page)
)
SELECT lot_id,title,variant_key,observed_at,price_cents,previous_at,previous_cents
FROM recent WHERE latest=1 AND observed_at>=? AND previous_at<observed_at
 AND price_cents>0 AND previous_cents>price_cents
 AND variant_key IS previous_variant
ORDER BY (previous_cents-price_cents)*1.0/previous_cents DESC,lot_id LIMIT 30`;

export async function readPriceDrops(db: Database, now = new Date()) {
  const from = new Date(+now - 30*86400000).toISOString();
  const fresh = new Date(+now - 48*3600000).toISOString();
  const {results} = await db.prepare(priceDropQuery).bind(from,now.toISOString(),fresh).all<PriceRow>();
  return results.filter(row => /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.lot_id))
    .map(row => ({...row, percent:100*(row.previous_cents-row.price_cents)/row.previous_cents,
      source:"https://gradedcardcenter.com/item/"+row.lot_id}));
}

export async function getPriceDrops() {
  try {
    const {getCloudflareContext} = await import("@opennextjs/cloudflare");
    const {env} = await getCloudflareContext({async:true});
    const db = (env as {SALES_DB?: Database}).SALES_DB;
    return db ? await readPriceDrops(db) : null;
  } catch { return null; }
}
