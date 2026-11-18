export type CataloguePrice = {
  low: number;
  updatedAt: string;
  stale: boolean;
};

export function readCataloguePrice(pricing: unknown, now = Date.now()): CataloguePrice | null {
  if (!pricing || typeof pricing !== "object" || !("cardmarket" in pricing)) return null;
  const value = pricing.cardmarket;
  if (!value || typeof value !== "object") return null;

  const { unit, low, updated } = value as Record<string, unknown>;
  if (unit !== "EUR" || typeof low !== "number" || !Number.isFinite(low) || low <= 0) return null;
  if (typeof updated !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(updated)) return null;

  const timestamp = Date.parse(updated);
  if (!Number.isFinite(timestamp) || timestamp > now) return null;
  return { low, updatedAt: new Date(timestamp).toISOString(), stale: now - timestamp > 48 * 60 * 60 * 1000 };
}

export type CatalogueQuote = CataloguePrice & {
  currency: "EUR" | "USD";
  provider: "Cardmarket" | "TCGplayer";
  marketLanguage: null;
  variant?: string;
};

export function readCatalogueQuote(pricing: unknown, now = Date.now()): CatalogueQuote | null {
  const european = readCataloguePrice(pricing, now);
  if (european) return { ...european, currency: "EUR", provider: "Cardmarket", marketLanguage: null };
  if (!pricing || typeof pricing !== "object") return null;

  const { cardmarket, tcgplayer } = pricing as Record<string, unknown>;
  if (cardmarket && typeof cardmarket === "object") {
    const entry = cardmarket as Record<string, unknown>;
    const holo = readCataloguePrice({ cardmarket: { ...entry, low: entry["low-holo"] } }, now);
    if (holo) return { ...holo, currency: "EUR", provider: "Cardmarket", marketLanguage: null, variant: "holo" };
  }

  if (!tcgplayer || typeof tcgplayer !== "object" || !("unit" in tcgplayer) || tcgplayer.unit !== "USD" ||
      !("updated" in tcgplayer)) return null;
  let best: CatalogueQuote | null = null;
  for (const [variant, entry] of Object.entries(tcgplayer)) {
    if (!entry || typeof entry !== "object" || !("lowPrice" in entry)) continue;
    const quote = readCataloguePrice({ cardmarket: { unit: "EUR", low: entry.lowPrice, updated: tcgplayer.updated } }, now);
    if (quote && (!best || quote.low < best.low)) {
      best = { ...quote, currency: "USD", provider: "TCGplayer", marketLanguage: null, variant };
    }
  }
  return best;
}
