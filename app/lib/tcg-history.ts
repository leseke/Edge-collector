export type HistoricalObservation = {
  productId: string; snapshotId: string; observedAt: string;
  source: string; currency: string; priceKind: string;
  low: number | null; availability: string; sourceUpdatedAt: string | null;
  reportSha256: string;
};

export function indexTcgHistory(observations: HistoricalObservation[]) {
  const index = new Map<string, HistoricalObservation[]>();
  const seen = new Set<string>();
  for (const item of observations) {
    if (!/^pokemon_card_[a-zA-Z0-9_.-]+$/.test(item.productId) ||
        !/^\d+-\d+$/.test(item.snapshotId) ||
        !/^[a-f0-9]{64}$/.test(item.reportSha256) ||
        !Number.isFinite(Date.parse(item.observedAt))) continue;
    const key = JSON.stringify([item.productId, item.snapshotId, item.source, item.currency, item.priceKind]);
    if (seen.has(key)) continue;
    seen.add(key);
    const row = {...item, low: typeof item.low === "number" && Number.isFinite(item.low) && item.low > 0 ? item.low : null};
    const group = index.get(item.productId) ?? [];
    group.push(row);
    index.set(item.productId, group);
  }
  for (const group of index.values()) group.sort((a,b) => Date.parse(a.observedAt) - Date.parse(b.observedAt));
  return index;
}

export function compareIndicativePrices(previous: HistoricalObservation, current: HistoricalObservation): number | null {
  if (previous.productId !== current.productId || previous.source !== current.source ||
      previous.currency !== current.currency || previous.priceKind !== current.priceKind ||
      !previous.source || !previous.currency || !previous.priceKind ||
      previous.snapshotId === current.snapshotId ||
      !(Date.parse(previous.observedAt) < Date.parse(current.observedAt)) ||
      !previous.sourceUpdatedAt || !current.sourceUpdatedAt ||
      !(Date.parse(previous.sourceUpdatedAt) < Date.parse(current.sourceUpdatedAt)) ||
      previous.low === null || current.low === null ||
      !Number.isFinite(previous.low) || !Number.isFinite(current.low) ||
      previous.low <= 0 || current.low <= 0) return null;
  const change = (current.low / previous.low - 1) * 100;
  return Number.isFinite(change) ? change : null;
}
