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
