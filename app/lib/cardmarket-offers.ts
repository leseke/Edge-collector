import { euroCents } from "./listing-analysis";

export const cardmarketConditions = ["MT", "NM", "EX", "GD", "LP", "PL", "PO"] as const;
type Condition = typeof cardmarketConditions[number];

export type CardmarketOffer = {
  source: string;
  cents: number;
  condition: Condition;
  observedAt: string;
};

function isCondition(value: unknown): value is Condition {
  return cardmarketConditions.some(condition => condition === value);
}

export function cardmarketProductUrl(value: string): string | null {
  if (value.length > 1000) return null;
  try {
    const url = new URL(value);
    if (url.origin !== "https://www.cardmarket.com" && url.origin !== "https://cardmarket.com") return null;
    if (url.username || url.password ||
        !/^\/[a-z]{2}\/Pokemon\/Products\/Singles\/[^/]+\/[^/]+\/?$/.test(url.pathname)) return null;
    return "https://www.cardmarket.com" + url.pathname.replace(/\/$/, "");
  } catch {
    return null;
  }
}

export function observedCardmarketOffer(url: string, price: string, condition: string, observedAt: string): CardmarketOffer | null {
  const source = cardmarketProductUrl(url);
  const cents = euroCents(price);
  if (!source || cents === null || cents <= 0 || !isCondition(condition) || !Number.isFinite(Date.parse(observedAt))) return null;
  return { source, cents, condition, observedAt };
}

export function cardmarketOfferStorageKey(cardId: string, language: string) {
  return "edge.cardmarket.asking.v1:" + cardId + ":" + language;
}

export function readCardmarketOffers(raw: string | null): CardmarketOffer[] {
  try {
    const data: unknown = JSON.parse(raw ?? "[]");
    if (!Array.isArray(data)) return [];
    return data.slice(0, 20).flatMap(row => {
      if (!row || typeof row.source !== "string" || !Number.isSafeInteger(row.cents) ||
          row.cents <= 0 || !isCondition(row.condition) || typeof row.observedAt !== "string" ||
          !Number.isFinite(Date.parse(row.observedAt))) return [];
      const source = cardmarketProductUrl(row.source);
      return source ? [{ source, cents: row.cents, condition: row.condition, observedAt: row.observedAt }] : [];
    });
  } catch {
    return [];
  }
}
