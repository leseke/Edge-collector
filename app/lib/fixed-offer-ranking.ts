import { canonical, comparableSales, listingCardKey } from "./comparable-sales";
import { estimateDeliveredCost } from "./delivered-cost";
import type { SaleVariant } from "./radar-paid-sales";
import type { getGccActiveListings } from "./gcc-active-listings";

export type ListingPage = NonNullable<Awaited<ReturnType<typeof getGccActiveListings>>>;
const day = 86_400_000;

export function rankFixedOffers(items: ListingPage["items"], variants: SaleVariant[], today: string) {
  const seriesActivity = new Map<string, { recent: Set<string>; previous: Set<string> }>();
  const now = Date.parse(today);
  for (const variant of variants) {
    const [kind, year, set] = canonical(variant.key).split(":");
    if (kind !== "carte") continue;
    const series = year + ":" + set;
    const activity = seriesActivity.get(series) ?? { recent: new Set<string>(), previous: new Set<string>() };
    for (const sale of variant.paidSales) {
      const age = (now - Date.parse(sale.day)) / day;
      if (age >= 0 && age < 14) (age < 7 ? activity.recent : activity.previous).add(sale.id);
    }
    seriesActivity.set(series, activity);
  }
  const ranked = items.flatMap(item => {
    const cost = estimateDeliveredCost(item.cents);
    const key = item.comparableCard && listingCardKey(item.title, item.variant, item.series);
    if (!cost || !key) return [];
    const history = comparableSales(variants, key, "gcc-" + item.id, today);
    const median = history?.median ?? null;
    const sales = history?.exact ?? [];
    const gap = median === null ? null : median - cost.estimate;
    const activity = seriesActivity.get(key.split(":").slice(1, 3).join(":"));
    const recent = activity?.recent.size ?? 0;
    const previous = activity?.previous.size ?? 0;
    const reason = gap !== null && gap > 0 ? "gap" : sales.length < 2 && recent >= 3 && recent >= 2 * previous ? "series" :
      sales.length === 1 ? "single" : null;
    return reason ? [{ item, reason, cost: cost.estimate, median, recent, previous, gap, count: sales.length, last: sales[0] }] : [];
  });
  const priority = (reason: string) => reason === "gap" ? 0 : reason === "series" ? 1 : 2;
  return ranked.sort((a, b) => priority(a.reason) - priority(b.reason) ||
    (b.gap ?? 0) / (b.median || 1) - (a.gap ?? 0) / (a.median || 1) ||
    b.recent - a.recent || a.item.id.localeCompare(b.item.id));
}
