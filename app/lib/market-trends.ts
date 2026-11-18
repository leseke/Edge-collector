export type TrendSale = { variant_key: string; sold_day: string; price_cents: number };

export function compareMarketWindows(rows: TrendSale[], today: string) {
  const asOf = Date.parse(today + "T00:00:00Z");
  const byVariant = new Map<string, number[][]>();
  for (const row of rows) {
    const age = (asOf - Date.parse(row.sold_day + "T00:00:00Z")) / 86_400_000;
    if (!(age >= 0 && age < 360) || !Number.isSafeInteger(row.price_cents) || row.price_cents <= 0) continue;
    const windows = byVariant.get(row.variant_key) ?? Array.from({ length: 12 }, () => [] as number[]);
    windows[Math.floor(age / 30)].push(row.price_cents);
    byVariant.set(row.variant_key, windows);
  }
  return [...byVariant].flatMap(([key, windows]) => {
    const stats = windows.map(values => {
      if (values.length < 3) return null;
      values.sort((a, b) => a - b);
      const middle = (values.length - 1) / 2;
      return { count: values.length, median: (values[Math.floor(middle)] + values[Math.ceil(middle)]) / 2 };
    });
    const [current, prior] = stats;
    if (!current || !prior) return [];
    const priceChange = Math.round(100 * (current.median / prior.median - 1));
    const scenario = direction(current, prior);
    let analogues = 0, continued = 0;
    // Use independent three-window samples and exclude the two current windows.
    for (let i = 2; i + 2 < stats.length && scenario !== "INDETERMINE"; i += 3) {
      const [after, signal, before] = stats.slice(i, i + 3);
      if (!after || !signal || !before || direction(signal, before) !== scenario) continue;
      analogues++;
      const change = after.median - signal.median;
      if (scenario === "HAUSSIER" ? change > 0 : change < 0) continued++;
    }
    return [{ key, recentMedian: current.median, priorMedian: prior.median, priceChange,
      recentCount: current.count, priorCount: prior.count, scenario, analogues, continued }];
  });
}

function direction(current: {count: number; median: number}, prior: {count: number; median: number}) {
  if (current.count < prior.count) return "INDETERMINE";
  if (100 * current.median >= 110 * prior.median) return "HAUSSIER";
  if (100 * current.median <= 90 * prior.median) return "BAISSIER";
  return "INDETERMINE";
}
