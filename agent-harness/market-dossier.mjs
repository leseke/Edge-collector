// Deterministic, evidence-constrained dossier built from a trusted D1 SELECT result.
// Produces an investigation candidate, NOT an investment recommendation.
import { normalizeD1Export } from "./export-d1.mjs";
import { assessMarket } from "./market-assessment.mjs";

export function buildMarketDossiers(payload, now = new Date().toISOString()) {
  const rows = normalizeD1Export(payload);
  const productIds = [...new Set(rows.map(r => r.product_id))].sort();
  return {
    schemaVersion: 1,
    generatedAt: now,
    provenance: "D1_TCGDEX_INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE",
    dataIsSynthetic: false,
    totalObservations: rows.length,
    dossiers: productIds.map(productId => {
      const assessment = assessMarket(rows, productId, now);
      return {
        productId,
        decision: "INVESTIGATE",
        hypothesisStatus: "UNVERIFIED",
        facts: {
          observationCount: assessment.observationCount,
          independentDays: assessment.independentDays,
          latestIndicativePriceCents: assessment.latestIndicativePriceCents,
          indicativeChangePercent: assessment.indicativeChangePercent,
          latestAgeHours: assessment.latestAgeHours,
        },
        weakSignals: [],
        inferences: [],
        bets: [],
        evidenceGaps: assessment.reasons,
        catalysts: [],
        risks: ["INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE", "NO_COMPLETED_SALES_OR_VOLUME_EVIDENCE"],
        entryHypothesis: null,
        exitHypothesis: null,
        purchaseAuthorized: false,
      };
    })
  };
}
