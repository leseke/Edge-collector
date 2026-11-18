import { readBoundedText } from "../../cloud/collector/src/bounded.mjs";

const gcc = "https://gradedcardcenter.com";
export const gccListingPages = {
  auction: gcc + "/filtres/auctions?categories=%5B%22Pokemon%22%5D",
  fixed: gcc + "/filtres/fixed-price?categories=%5B%22Pokemon%22%5D",
};

type ListingKind = keyof typeof gccListingPages;
type ActiveListing = { id: string; title: string; variant: string; cents: number; ends: string | null; image: string | null };
type Relevé = { checkedAt: string; items: ActiveListing[] };

const entities: Record<string, string> = { amp: "&", quot: '"', apos: "'", nbsp: " ", lt: "<", gt: ">" };
function decode(input: string) {
  return input.replace(/&(#x[\da-f]+|#\d+|amp|quot|apos|nbsp|lt|gt);/gi, (entity, code: string) => {
    if (code.startsWith("#")) {
      const value = code[1].toLowerCase() === "x" ? parseInt(code.slice(2), 16) : Number(code.slice(1));
      return value > 0 && value <= 0x10ffff ? String.fromCodePoint(value) : entity;
    }
    return entities[code.toLowerCase()] ?? entity;
  }).trim();
}

const paris = new Intl.DateTimeFormat("fr-FR", {
  timeZone: "Europe/Paris", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function futureAuction(ends: string, asOf: Date) {
  const [, day, month, hour, minute] = ends.match(/^(\d{2})\/(\d{2}) @ (\d{2})h(\d{2})$/) ?? [];
  if (!day || +hour > 23 || +minute > 59 || +month < 1 || +month > 12 || +day < 1 || +day > 31) return false;
  const parts = Object.fromEntries(paris.formatToParts(asOf).map(part => [part.type, part.value]));
  const year = Number(parts.year) + (parts.month === "12" && month === "01" ? 1 : 0);
  if (new Date(Date.UTC(year, +month, 0)).getUTCDate() < +day) return false;
  return `${year}${month}${day}${hour}${minute}` > `${parts.year}${parts.month}${parts.day}${parts.hour}${parts.minute}`;
}

export function readGccActiveListings(html: string, kind: ListingKind, asOf: Date) {
  const results = new Map<string, ActiveListing>();
  const clean = html.replace(/<(?:script|style)\b[^>]*>[\s\S]*?<\/(?:script|style)>/gi, "").replace(/<!--[\s\S]*?-->/g, "");
  const cards = clean.split(/<div\b[^>]*\bclass="bg-surface-2 relative flex flex-col overflow-hidden rounded-\[10px\] h-full"[^>]*>/).slice(1);
  if (!cards.length) {
    if (/\b0\s+résultats?\b/i.test(clean)) return [];
    throw new Error("GCC grid unavailable");
  }
  for (const card of cards) {
    const id = card.match(/<a\b[^>]*\bhref="\/item\/([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})"/)?.[1];
    const title = decode(card.match(/<p\b[^>]*class="text-base font-semibold text-white truncate"[^>]*>([^<>]+)<\/p>/)?.[1] ?? "");
    const details = decode(card.match(/<p\b[^>]*class="text-\[11px\] font-medium text-gray-100 truncate"[^>]*>([^<>]+)<\/p>/)?.[1] ?? "");
    if (!id || !title || !/^Pok[eé]mon\s*•/i.test(details)) continue;
    const rawPrice = decode(card.match(/<p\b[^>]*class="text-2xl font-semibold text-white"[^>]*>([^<>]+)<\/p>/)?.[1] ?? "");
    if (!/^\d[\d'’ ]*(?:[,.]\d{1,2})?\s*€$/.test(rawPrice)) continue;
    const cents = Math.round(100 * Number(rawPrice.replace(/['’\s€]/g, "").replace(",", ".")));
    if (!Number.isSafeInteger(cents) || cents <= 0) continue;
    const ends = card.match(/Fin le (\d{2}\/\d{2} @ \d{2}h\d{2})/)?.[1] ?? null;
    const action = kind === "auction" ? "Enchérir" : "Acheter";
    const hasAction = [...card.matchAll(/<button\b([^>]*)>\s*(Enchérir|Acheter)\s*<\/button>/g)]
      .some(([, attrs, label]) => label === action && !/\sdisabled(?:=|\s|$)/.test(attrs));
    if (!hasAction || (kind === "auction" ? !ends || !futureAuction(ends, asOf) : !!ends)) continue;
    const image = card.match(/<img\b[^>]*\bsrc="(https:\/\/cdn\.gradedcardcenter\.com\/image\/width=1000,fit=contain,format=webp,quality=65\/item\/[\w-]+)"/)?.[1] ?? null;
    const variant = details.replace(/^Pok[eé]mon\s*•\s*/i, "")
      .replace(/^(French|English|Italian|Japanese|Spanish|German)(?=\s*•)/,
        language => ({ French: "Français", English: "Anglais", Italian: "Italien", Japanese: "Japonais", Spanish: "Espagnol", German: "Allemand" } as Record<string, string>)[language]);
    results.set(id, { id, title, variant, cents, ends, image });
    if (results.size === 8) break;
  }
  return [...results.values()];
}

export async function getGccActiveListings(kind: ListingKind): Promise<Relevé | null> {
  const key = new Request(`https://edge-radar-preview-1c14d55.ylan-seke.workers.dev/_gcc-public-listings-v1/${kind}`);
  const cache = typeof caches === "undefined" ? undefined : (caches as CacheStorage & { default?: Cache }).default;
  try {
    const cached = await cache?.match(key).catch(() => undefined);
    if (cached) {
      const data: Relevé = await cached.json();
      return { ...data, items: data.items.filter(item => !item.ends || futureAuction(item.ends, new Date())) };
    }
    const response = await fetch(gccListingPages[kind], {
      headers: { Accept: "text/html", "Accept-Language": "fr" },
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(7_000),
    });
    if (!response.ok || !response.headers.get("content-type")?.includes("text/html")) return null;
    const html = await readBoundedText(response, 1_500_000);
    const now = new Date();
    const data = { checkedAt: now.toISOString(), items: readGccActiveListings(html, kind, now) };
    await cache?.put(key, Response.json(data, { headers: { "Cache-Control": "public, max-age=120" } })).catch(() => {});
    return data;
  } catch {
    return null;
  }
}
