import { validateProposal } from "./proposal.mjs";

/**
 * A deterministic read-only boundary for a future dsh ctx.tools adapter.
 * The caller supplies a trusted D1 export; this module never fetches, writes,
 * executes commands, or accepts credentials.
 */
export function inspectObservations(rows, productId) {
  if (!/^[a-zA-Z0-9_-]{1,120}$/.test(productId)) throw new Error("invalid_product");
  if (!Array.isArray(rows) || rows.length > 10000) throw new Error("invalid_rows");
  const matched = rows.filter(row => row && row.product_id === productId)
    .map(row => {
      if (row.price_kind !== "AGGREGATE" || row.currency !== "EUR") throw new Error("unsupported_provenance");
      if (typeof row.source_url !== "string") throw new Error("untrusted_source");
      let source;
      try { source = new URL(row.source_url); } catch { throw new Error("untrusted_source"); }
      if (source.protocol !== "https:" || source.hostname !== "api.tcgdex.net" || source.username || source.password || source.port) throw new Error("untrusted_source");
      if (typeof row.observed_at !== "string" || !/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})$/.test(row.observed_at) || Number.isNaN(Date.parse(row.observed_at))) throw new Error("invalid_time");
      if (row.price_cents !== null && (!Number.isSafeInteger(row.price_cents) || row.price_cents < 0)) throw new Error("invalid_price");
      return { productId, observedAt: row.observed_at, priceCents: row.price_cents, currency: "EUR", priceKind: "AGGREGATE", sourceUrl: row.source_url };
    })
    .sort((a,b) => a.observedAt.localeCompare(b.observedAt));
  if (matched.length > 500) throw new Error("too_many_observations");
  const first = matched.at(-2), latest = matched.at(-1);
  return Object.freeze({
    productId, provenance: "INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE",
    observations: matched.length,
    latest: latest ?? null,
    previous: first ?? null,
    changePercent: first?.priceCents && latest?.priceCents !== null && latest?.priceCents !== undefined
      ? Math.round(10000 * (latest.priceCents - first.priceCents) / first.priceCents) / 100 : null,
    purchaseAuthorized: false
  });
}
export function acceptAgentProposal(raw) { return validateProposal(raw); }
