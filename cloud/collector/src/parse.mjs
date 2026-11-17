// Strictly parse a TCGdex Cardmarket indicative aggregate, never a completed sale.
export function parseIndicativePrice(raw) {
  if (typeof raw !== "string" || raw.length > 128000) throw new Error("invalid_payload_size");
  const data = JSON.parse(raw);
  if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("invalid_payload");
  const market = data.pricing?.cardmarket;
  if (!market || typeof market !== "object" || Array.isArray(market)) throw new Error("no_cardmarket_pricing");
  const low = market.low;
  if (typeof low !== "number" || !Number.isFinite(low) || low < 0 || low > 1000000) throw new Error("invalid_cardmarket_low");
  const cents = Math.round(low * 100);
  if (!Number.isSafeInteger(cents)) throw new Error("invalid_cents");
  const updated = typeof market.updated === "string" && !Number.isNaN(Date.parse(market.updated)) ? market.updated : null;
  return { price: cents, updated };
}
