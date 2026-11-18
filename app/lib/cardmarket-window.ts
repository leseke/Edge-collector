export function readCardmarketWindow(data: unknown, now = Date.now()) {
  if (!data || typeof data !== "object") return null;
  const price = data as Record<string, unknown>;
  const { avg7, avg30, updated, unit } = price;
  if (unit !== "EUR" || typeof avg7 !== "number" || typeof avg30 !== "number" ||
      !Number.isFinite(avg7) || !Number.isFinite(avg30) || avg7 <= 0 || avg30 <= 0 ||
      typeof updated !== "string") return null;
  const timestamp = Date.parse(updated);
  if (!Number.isFinite(timestamp) || timestamp > now) return null;
  return { avg7, avg30, updated, stale: now - timestamp > 48 * 60 * 60 * 1000,
    percent: 100 * (avg7 - avg30) / avg30 };
}
