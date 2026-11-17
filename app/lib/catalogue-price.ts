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
