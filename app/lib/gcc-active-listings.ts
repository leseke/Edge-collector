import { readBoundedText } from "../../cloud/collector/src/bounded.mjs";

const gcc = "https://gradedcardcenter.com";
const pokemon = "categories=%5B%22Pokemon%22%5D";
export const gccListingPages = {
  auction: gcc + "/filtres/auctions?" + pokemon,
  fixed: gcc + "/filtres/fixed-price?" + pokemon,
  closed: gcc + "/filtres?" + pokemon + "&status=SOLD",
};

export type GccListingKind = keyof typeof gccListingPages;
type Lot = { id: string; title: string; variant: string; cents: number | null; ends: string | null; soldAt: string | null; image: string | null; awaitingPayment: boolean; series: string | null };
type GccPage = { checkedAt: string; items: Lot[]; page: number; nextCursor: string | null; total: number | null };
type GccRow = {
  id?: string; status?: string; sellingType?: string; priceInCents?: number; endTime?: string; soldAt?: string;
  item?: { title?: string; subtitle?: string; rectoImageKey?: string; collectible?: { category?: string; set?: string } };
};

const labels: Record<string, string> = { French: "Français", English: "Anglais", Italian: "Italien", Japanese: "Japonais", Spanish: "Espagnol", German: "Allemand" };
const pageSize = 24;
const positiveInt = (n: unknown): n is number => typeof n === "number" && Number.isSafeInteger(n) && n > 0;
const timestamp = (value: unknown): value is string => typeof value === "string" && /^\d{4}-\d\d-\d\dT/.test(value) && Number.isFinite(Date.parse(value));

export function gccCursor(value: unknown): string | null {
  return typeof value === "string" && /^[A-Za-z0-9_-]{10,768}$/.test(value) ? value : null;
}

export function gccPageUrl(kind: GccListingKind, cursor: string | null, series?: string | null) {
  const url = new URL("https://api.gradedcardcenter.com/on-sale-items");
  const query = url.searchParams;
  query.set("categories", "Pokemon");
  query.set("limit", String(pageSize));
  if (kind === "closed" && series) query.set("sets", series);
  if (kind === "closed") {
    query.set("status", "SOLD");
    query.append("status", "WAITING_FOR_PAYMENT");
  } else {
    query.set("status", "ON_SALE");
    query.set("sellingTypeGroup", kind === "auction" ? "AUCTION" : "FIXED_PRICE");
  }
  query.set("sortType", kind === "closed" ? "SOLD_LAST" : kind === "auction" ? "ENDING_SOON" : "MOST_RECENT");
  if (cursor) query.set("cursor", cursor);
  else query.set("includeCounts", "true");
  return url;
}

function isOpen(lot: Lot, now: Date) {
  return !lot.ends || Date.parse(lot.ends) > +now;
}

export function readGccPage(data: unknown, kind: GccListingKind, now: Date): GccPage {
  if (!data || typeof data !== "object" || !("results" in data) || !Array.isArray(data.results) || !("info" in data)) throw new Error("GCC page unavailable");
  const info = data.info as { currentPage?: unknown; nextCursor?: unknown; counts?: { total?: unknown; auctionCount?: unknown; fixedPriceCount?: unknown } } | null;
  if (!positiveInt(info?.currentPage) || data.results.length > pageSize) throw new Error("Invalid GCC page");

  const items = new Map<string, Lot>();
  for (const row of data.results as (GccRow | null)[]) {
    if (!row || typeof row.id !== "string" || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.id)) continue;
    const { item } = row;
    if (item?.collectible?.category !== "Pokemon" || typeof item.title !== "string" || !item.title.trim()) continue;
    const ends = kind === "auction" && timestamp(row.endTime) ? row.endTime : null;
    if (kind === "auction" && (!ends || row.sellingType === "FIXED_PRICE")) continue;
    if (kind === "fixed" && row.sellingType !== "FIXED_PRICE") continue;
    if (kind === "closed" ? !["SOLD", "WAITING_FOR_PAYMENT"].includes(row.status ?? "") : row.status !== "ON_SALE") continue;
    const subtitle = typeof item.subtitle === "string" ? item.subtitle.replace(/^Pok[eé]mon\s*•\s*/i, "") : "";
    const imageKey = item.rectoImageKey;
    const sourceImage = typeof imageKey === "string" && /^item\/[A-Za-z0-9_-]{1,120}$/.test(imageKey)
      ? "https://cdn.gradedcardcenter.com/image/width=300,fit=contain,format=webp,quality=65/" + imageKey : null;
    const lot = {
      id: row.id, title: item.title.slice(0, 180), cents: positiveInt(row.priceInCents) ? row.priceInCents : null, ends,
      variant: subtitle.slice(0, 250).replace(/^(French|English|Italian|Japanese|Spanish|German)(?=\s*•)/, lang => labels[lang]),
      image: sourceImage, soldAt: kind === "closed" && timestamp(row.soldAt) ? row.soldAt : null,
      awaitingPayment: row.status === "WAITING_FOR_PAYMENT",
      series: gccSeries(item.collectible.set),
    };
    if (isOpen(lot, now)) items.set(lot.id, lot);
  }
  const total = kind === "auction" ? info.counts?.auctionCount : kind === "fixed" ? info.counts?.fixedPriceCount : info.counts?.total;
  return { checkedAt: now.toISOString(), items: [...items.values()], page: info.currentPage,
    nextCursor: gccCursor(info.nextCursor), total: positiveInt(total) || total === 0 ? total : null };
}

export async function getGccActiveListings(kind: GccListingKind, cursor: string | null, series?: string | null): Promise<GccPage | null> {
  const key = new Request(`https://edge-radar-preview-1c14d55.ylan-seke.workers.dev/_gcc-catalogue-v2/${kind}/${cursor ?? "first"}?series=${encodeURIComponent(series ?? "")}`);
  const cache = typeof caches === "undefined" ? undefined : (caches as CacheStorage & { default?: Cache }).default;
  try {
    const cached = await cache?.match(key).catch(() => undefined);
    if (cached) {
      const data: GccPage = await cached.json();
      return { ...data, items: data.items.filter(item => isOpen(item, new Date())) };
    }
    const response = await fetch(gccPageUrl(kind, cursor, series), {
      headers: { Accept: "application/json", "Accept-Language": "fr" },
      redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) return null;
    const data = readGccPage(JSON.parse(await readBoundedText(response, 1_500_000)), kind, new Date());
    await cache?.put(key, Response.json(data, { headers: { "Cache-Control": "public, max-age=120" } })).catch(() => {});
    return data;
  } catch {
    return null;
  }
}

export function gccSeries(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const series = value.trim();
  return series && series.length <= 100 && !/[\u0000-\u001f\u007f]/.test(series) ? series : null;
}

export async function getGccSeries(): Promise<string[]> {
  const url = new URL("https://api.gradedcardcenter.com/on-sale-items/field-occurence");
  url.search = "categories=Pokemon&fieldName=sets&status=SOLD&status=WAITING_FOR_PAYMENT&take=200";
  const cache = typeof caches === "undefined" ? undefined : (caches as CacheStorage & { default?: Cache }).default;
  const key = "https://edge-radar-preview-1c14d55.ylan-seke.workers.dev/_gcc-series-v1";
  try {
    const cached = await cache?.match(key).catch(() => undefined);
    if (cached) return await cached.json() as string[];
    const response = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(6_000), cache: "no-store" });
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) return [];
    const rows: unknown = JSON.parse(await readBoundedText(response, 100_000));
    if (!Array.isArray(rows)) return [];
    const series = [...new Set(rows.slice(0, 200).flatMap(row => {
      const label = gccSeries(row?.id);
      return label ? [label] : [];
    }))].sort((a, b) => a.localeCompare(b, "fr"));
    await cache?.put(key, Response.json(series, { headers: { "Cache-Control": "public, max-age=3600" } })).catch(() => {});
    return series;
  } catch {
    return [];
  }
}
