import { readMarketplaceCaptures, reviewedMarketplaceCaptures } from "./marketplace-captures";

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

const noctali = {
  name: "Noctali VMAX 215/203",
  releasedOn: "2021-08-27",
  releaseSource: "https://press.pokemon.com/en/MEDIA-ALERT-Pokemon-Trading-Card-Game-Sword-ShieldEvolving-Skies-Expan",
};
const ectoplasma = {
  name: "Ectoplasma VMAX 157/264",
  releasedOn: "2021-11-12",
  releaseSource: "https://press.pokemon.com/en/Pokemon-TCG-Sword-ShieldFusion-Strike",
};

// Each GCC lot below has a public sale price and an explicit paid status.
function gccPaidSale(lotId: string, day: string, cents: number): Sale {
  return {
    id: "gcc-" + lotId,
    day,
    cents,
    source: "https://gradedcardcenter.com/item/" + lotId,
  };
}

export const reviewedCardLiquidity: CardLiquidityEvidence[] = [
  {
    ...noctali,
    variant: "FR · Unlimited · PCA 9",
    listings: readMarketplaceCaptures(reviewedMarketplaceCaptures, "swsh7-215:fr:unlimited:pca:9"),
    paidSales: [gccPaidSale("8c29e2ba-d560-49b9-945b-6a8ac21a8978", "2026-05-27", 175000)],
  },
  {
    ...noctali,
    variant: "FR · Unlimited · PCA 9.5",
    listings: readMarketplaceCaptures(reviewedMarketplaceCaptures, "swsh7-215:fr:unlimited:pca:9.5"),
    paidSales: [
      gccPaidSale("9e70c3a8-8ed4-4bfe-a988-63d83bea6220", "2026-03-14", 180000),
      gccPaidSale("7237a6f7-cfe8-4708-b3b6-274a8b46fd4d", "2026-06-01", 190000),
    ],
  },
  {
    ...noctali,
    variant: "FR · Unlimited · PSA 10",
    listings: readMarketplaceCaptures(reviewedMarketplaceCaptures, "swsh7-215:fr:unlimited:psa:10"),
    paidSales: [
      gccPaidSale("a42e4e3d-6427-498f-971e-8e489fe63127", "2026-02-15", 320000),
      gccPaidSale("6bb74cb4-5910-4bc1-ab31-45f9dd1b88f6", "2026-02-26", 290000),
    ],
  },
  {
    ...ectoplasma,
    variant: "FR · Unlimited · PCA 9.5",
    listings: readMarketplaceCaptures(reviewedMarketplaceCaptures, "swsh8-157:fr:unlimited:pca:9.5"),
    paidSales: [gccPaidSale("39a0c666-270e-46f6-b520-359b81362a53", "2026-09-12", 8500)],
  },
  {
    ...ectoplasma,
    variant: "FR · Unlimited · PSA 10",
    listings: readMarketplaceCaptures(reviewedMarketplaceCaptures, "swsh8-157:fr:unlimited:psa:10"),
    paidSales: [
      gccPaidSale("c7a9d32f-c531-4993-afd0-c3f800ccc415", "2026-03-03", 13000),
      gccPaidSale("c06c8964-11d2-43e3-b91c-cb6ac6a1514c", "2026-05-29", 20000),
      gccPaidSale("fc56512c-6d10-4f93-919d-17b81665f676", "2026-09-06", 19000),
    ],
  },
];
