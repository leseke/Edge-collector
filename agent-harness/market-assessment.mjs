import { inspectObservations } from "./edge-readonly-tool.mjs";

/**
 * A conservative, reproducible market assessment. No model, no fabricated sales.
 * A delta between indicative aggregate snapshots is NOT a trading signal.
 */
export function assessMarket(rows, productId, now = new Date().toISOString()) {
  const snapshot = inspectObservations(rows, productId);
  if (!Number.isFinite(Date.parse(now))) throw new Error("invalid_assessment_time");
  const matches = rows.filter(r => r?.product_id === productId);
  const latestTime = snapshot.latest?.observedAt;
  const ageHours = latestTime ? Math.max(0, (Date.parse(now) - Date.parse(latestTime)) / 3600000) : null;
  const uniqueDays = new Set(matches.map(r => r.observed_at.slice(0, 10))).size;
  const reasons = [];
  if (snapshot.observations === 0) reasons.push("NO_OBSERVATIONS");
  if (snapshot.observations < 3) reasons.push("INSUFFICIENT_HISTORY");
  if (uniqueDays < 3) reasons.push("INSUFFICIENT_INDEPENDENT_DAYS");
  if (ageHours === null || ageHours > 48) reasons.push("STALE_OR_MISSING_OBSERVATION");
  reasons.push("NO_COMPLETED_SALES_OR_VOLUME_EVIDENCE");
  return {
    productId, classification: "FACT_LIMITED",
    signal: "INSUFFICIENT_EVIDENCE",
    reasons,
    latestIndicativePriceCents: snapshot.latest?.priceCents ?? null,
    indicativeChangePercent: snapshot.changePercent,
    observationCount: snapshot.observations,
    independentDays: uniqueDays,
    latestAgeHours: ageHours === null ? null : Math.round(ageHours * 10) / 10,
    evidenceKind: "FACT",
    demandConfirmed: false,
    completedSalesConfirmed: false,
    opportunityRejected: false,
    hypothesisAllowed: true,
    purchaseAuthorized: false
  };
}
