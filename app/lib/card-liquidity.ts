type ListingSnapshot = { day: string; scope: string; listingIds: string[] };
type Sale = { id: string; day: string; cents: number; source: string };
export type CardLiquidityEvidence = {
  name: string;
  variant: string;
  releasedOn: string;
  releaseSource: string;
  listings: ListingSnapshot[];
  paidSales: Sale[];
};

const dayMs = 86_400_000;
const dayValue = (value: string) => Date.parse(value + "T00:00:00Z");

export function summarizeCardLiquidity(evidence: CardLiquidityEvidence, asOf: string) {
  const now = dayValue(asOf);
  const snapshots = evidence.listings
    .filter(snapshot => dayValue(snapshot.day) <= now)
    .sort((a, b) => b.day.localeCompare(a.day));
  const latest = snapshots[0];
  const previous = latest && snapshots.find(snapshot => snapshot.scope === latest.scope && snapshot.day < latest.day);
  const active = latest ? new Set(latest.listingIds).size : null;
  const paid = [...new Map(evidence.paidSales
    .filter(sale => dayValue(sale.day) <= now && Number.isSafeInteger(sale.cents) && sale.cents > 0)
    .sort((a, b) => a.day.localeCompare(b.day))
    .map(sale => [sale.id, sale])).values()].sort((a, b) => b.day.localeCompare(a.day));
  const recent = paid.filter(sale => now - dayValue(sale.day) < 30 * dayMs);
  const baseline = paid.filter(sale => {
    const age = (now - dayValue(sale.day)) / dayMs;
    return age >= 30 && age < 60;
  });
  const median = (sales: Sale[]) => {
    const prices = sales.map(sale => sale.cents).sort((a, b) => a - b);
    const middle = Math.floor(prices.length / 2);
    return (prices[Math.floor((prices.length - 1) / 2)] + prices[middle]) / 2;
  };
  const enoughSales = recent.length >= 2 && baseline.length >= 2;
  const freshComparison = latest && previous &&
    now - dayValue(latest.day) <= 7 * dayMs &&
    dayValue(latest.day) - dayValue(previous.day) <= 30 * dayMs;
  const signal = !freshComparison || !enoughSales ? "INSUFFICIENT_EVIDENCE" :
    active! < new Set(previous.listingIds).size && recent.length >= baseline.length &&
    median(recent) >= median(baseline) ? "SUPPLY_TIGHTENING" : "NO_SIGNAL";
  return {
    signal,
    ageDays: Math.max(0, Math.floor((now - dayValue(evidence.releasedOn)) / dayMs)),
    listingDay: latest?.day ?? null,
    active,
    change: previous && active !== null ? active - new Set(previous.listingIds).size : null,
    previousDay: previous?.day ?? null,
    newlyObserved: previous ? new Set(latest.listingIds.filter(id => !previous.listingIds.includes(id))).size : null,
    saleWindows: [7, 30, 90].map(days => ({
      days,
      observed: paid.filter(sale => now - dayValue(sale.day) < days * dayMs).length,
    })),
    lastPaid: paid[0] ?? null,
  };
}

export const reviewedCardLiquidity: CardLiquidityEvidence[] = [{
  name: "Noctali VMAX 215/203",
  variant: "FR · Unlimited · PCA 9",
  releasedOn: "2021-08-27",
  releaseSource: "https://press.pokemon.com/en/MEDIA-ALERT-Pokemon-Trading-Card-Game-Sword-ShieldEvolving-Skies-Expan",
  listings: [],
  paidSales: [{
    id: "gcc-8c29e2ba-d560-49b9-945b-6a8ac21a8978",
    day: "2026-05-27",
    cents: 175000,
    source: "https://gradedcardcenter.com/item/8c29e2ba-d560-49b9-945b-6a8ac21a8978",
  }],
}];
