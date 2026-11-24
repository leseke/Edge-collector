import { assessPriceDrop, resaleFeePercent } from "../../../app/lib/listing-analysis";
import type { getGccActiveListings } from "../../../app/lib/gcc-active-listings";

type Lot = NonNullable<Awaited<ReturnType<typeof getGccActiveListings>>>["items"][number];
type SaleRow = { lot_id: string; sold_day: string; price_cents: number; source_url: string; variant_key: string };

export async function prepareOpportunityEvents(db: D1Database, lots: Lot[], observedAt: string) {
  const day = observedAt.slice(0,10);
  const oldest = new Date(Date.parse(observedAt) - 89*86400000).toISOString().slice(0,10);
  const keys = [...new Set(lots.flatMap(lot => lot.variantKey ? [lot.variantKey] : []))];
  const {results} = keys.length ? await db.prepare(`SELECT lot_id,sold_day,price_cents,source_url,variant_key FROM paid_market_sales
    WHERE variant_key IN (SELECT value FROM json_each(?)) AND sold_day BETWEEN ? AND ? AND collected_at<=?
    ORDER BY sold_day DESC,lot_id LIMIT 2001`).bind(JSON.stringify(keys),oldest,day,observedAt).all<SaleRow>() : {results: [] as SaleRow[]};
  // Truncated evidence is not a complete market reference.
  const variants = keys.map(key => ({key, paidSales: results.length > 2000 ? [] : results.filter(row =>
    row.variant_key === key && /^gcc-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.lot_id) &&
    row.source_url === "https://gradedcardcenter.com/item/" + row.lot_id.slice(4))
    .map(row => ({id:row.lot_id,day:row.sold_day,cents:row.price_cents,source:row.source_url}))}));
  const events = lots.flatMap(lot => {
    if (lot.cents === null || lot.cents <= 0) return [];
    const assessment = assessPriceDrop(lot,variants,day);
    const evidence = (variants.find(v=>v.key===lot.variantKey)?.paidSales ?? []).filter(s=>s.id!=="gcc-"+lot.id);
    return [{id:lot.id,variant:lot.variantKey,title:lot.title,ask:lot.cents,median:assessment.median,count:assessment.count,
      headroom:assessment.headroom,status:assessment.status,evidence}];
  });
  // Commit in the caller's guarded coverage batch. No purchase or capital filter.
  return events;
}
