export function euroCents(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d{1,7}(?:\.\d{1,2})?$/.test(normalized)) return null;
  const [euros, cents = ""] = normalized.split(".");
  return Number(euros) * 100 + Number(cents.padEnd(2, "0"));
}

export function analyzeListing(input: {
  askingCents: number;
  acquisitionFeesCents: number | null;
  exitNetCents: number | null;
  targetGainCents: number;
  budgetCents: number;
}) {
  const { askingCents, acquisitionFeesCents, exitNetCents, targetGainCents, budgetCents } = input;
  const cost = acquisitionFeesCents === null ? null : askingCents + acquisitionFeesCents;
  const gain = cost === null || exitNetCents === null ? null : exitNetCents - cost;
  const maxAsk = acquisitionFeesCents === null || exitNetCents === null ? null :
    Math.max(0, Math.min(budgetCents, exitNetCents - targetGainCents) - acquisitionFeesCents);
  const budgetExceeded = (cost ?? askingCents) > budgetCents;
  return { cost, gain, maxAsk, budgetExceeded };
}

type MarketSale = { id: string; day: string; cents: number; source: string };
const dayMs = 86_400_000;
export const resaleFeePercent = 10;

export function estimateListingMarket(sales: MarketSale[], asOf: string) {
  const now = Date.parse(asOf + "T00:00:00Z");
  const recentById = new Map<string, MarketSale>();
  for (const sale of sales) {
    const age = (now - Date.parse(sale.day + "T00:00:00Z")) / dayMs;
    if (!(age >= 0 && age < 365) || !Number.isSafeInteger(sale.cents) || sale.cents <= 0) continue;
    const prior = recentById.get(sale.id);
    if (!prior || sale.day > prior.day) recentById.set(sale.id, sale);
  }
  const history = [...recentById.values()].sort((a, b) => b.day.localeCompare(a.day));
  const recent = history.filter(sale => now - Date.parse(sale.day + "T00:00:00Z") < 90 * dayMs);
  const ordered = recent.map(sale => sale.cents).sort((a, b) => a - b);
  const midpoint = (ordered.length - 1) / 2;
  const conservativeGross = ordered.length >= 2 ? ordered[0] : null;
  const medianGross = ordered.length >= 2
    ? Math.floor((ordered[Math.floor(midpoint)] + ordered[Math.ceil(midpoint)]) / 2)
    : null;
  const conservativeNet = conservativeGross === null ? null :
    Math.floor(conservativeGross * (100 - resaleFeePercent) / 100);
  const oldest = history.at(-1);
  const horizonSupported = history.length >= 3 && oldest &&
    Date.parse(history[0].day + "T00:00:00Z") - Date.parse(oldest.day + "T00:00:00Z") >= 90 * dayMs;
  const historicalLow = horizonSupported ? Math.min(...history.map(sale => sale.cents)) : null;
  return { recent, history, conservativeGross, medianGross, conservativeNet, historicalLow };
}


// A market-only shortlist: capital never filters discovery.
export type OpportunityOffer = { id: string; variantKey: string | null; cents: number | null };
export function rankFixedOffers<T extends OpportunityOffer>(
  offers: T[], variants: { key: string; paidSales: MarketSale[] }[], asOf: string,
) {
  const byKey = new Map(variants.map(v => [v.key, v.paidSales]));
  const seen = new Set<string>();
  return offers.flatMap(offer => {
    if (seen.has(offer.id)) return [];
    seen.add(offer.id);
    if (!offer.variantKey || offer.cents === null || !Number.isSafeInteger(offer.cents) || offer.cents <= 0) return [];
    const source = "https://gradedcardcenter.com/item/" + offer.id;
    const market = estimateListingMarket((byKey.get(offer.variantKey) ?? []).filter(s => s.source !== source && s.id !== "gcc-" + offer.id), asOf);
    if (market.medianGross === null || market.conservativeNet === null || offer.cents >= market.medianGross) return [];
    const gapPercent = 100 * (market.medianGross - offer.cents) / market.medianGross;
    const headroomCents = market.conservativeNet - offer.cents;
    return [{ offer, gapPercent, headroomCents, medianCents: market.medianGross,
      ceilingBeforeAcquisitionFees: market.conservativeNet, comparableCount: market.recent.length,
      latestSaleDay: market.recent[0].day, evidence: market.recent }];
  }).sort((a,b) => Number(b.headroomCents > 0) - Number(a.headroomCents > 0) ||
    b.gapPercent - a.gapPercent || b.comparableCount - a.comparableCount || a.offer.id.localeCompare(b.offer.id));
}


export function assessPriceDrop(offer: OpportunityOffer, variants: { key: string; paidSales: MarketSale[] }[], asOf: string) {
  const matching = offer.variantKey ? variants.find(v => v.key === offer.variantKey) : undefined;
  const market = estimateListingMarket((matching?.paidSales ?? []).filter(s =>
    s.id !== "gcc-" + offer.id && s.source !== "https://gradedcardcenter.com/item/" + offer.id), asOf);
  if (offer.cents === null || offer.cents <= 0 || market.medianGross === null || market.conservativeNet === null) {
    return { status: "INSUFFICIENT" as const, count: market.recent.length, median: null, gapPercent: null, headroom: null };
  }
  const gapPercent = 100 * (market.medianGross - offer.cents) / market.medianGross;
  const headroom = market.conservativeNet - offer.cents;
  return { status: headroom > 0 ? "INVESTIGATE" as const : gapPercent > 0 ? "THIN_MARGIN" as const : "NO_DISCOUNT" as const,
    count: market.recent.length, median: market.medianGross, gapPercent, headroom };
}
