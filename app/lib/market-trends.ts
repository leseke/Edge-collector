export type TrendSale = { variant_key: string; sold_day: string; price_cents: number };

export function compareMarketWindows(rows: TrendSale[], today: string) {
  const asOf = Date.parse(today + "T00:00:00Z");
  const byVariant = new Map<string, { current: number[]; prior: number[] }>();
  for (const row of rows) {
    const age = (asOf - Date.parse(row.sold_day + "T00:00:00Z")) / 86_400_000;
    if (!(age >= 0 && age < 60) || !Number.isSafeInteger(row.price_cents) || row.price_cents <= 0) continue;
    const windows = byVariant.get(row.variant_key) ?? { current: [], prior: [] };
    windows[age < 30 ? "current" : "prior"].push(row.price_cents);
    byVariant.set(row.variant_key, windows);
  }
  return [...byVariant].flatMap(([key, { current, prior }]) => {
    if (current.length < 3 || prior.length < 3) return [];
    const median = (values: number[]) => {
      const ordered = [...values].sort((a, b) => a - b);
      return (ordered[Math.floor((ordered.length - 1) / 2)] + ordered[Math.ceil((ordered.length - 1) / 2)]) / 2;
    };
    const recentMedian = median(current);
    const priorMedian = median(prior);
    const priceChange = Math.round(100 * (recentMedian / priorMedian - 1));
    const scenario = priceChange >= 10 && current.length >= prior.length ? "HAUSSIER" :
      priceChange <= -10 && current.length >= prior.length ? "BAISSIER" : "INDETERMINE";
    return [{ key, recentMedian, priorMedian, priceChange, recentCount: current.length, priorCount: prior.length, scenario }];
  });
}
