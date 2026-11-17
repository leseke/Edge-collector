import { buildMarketDossiers } from "./market-dossier.mjs";

/**
 * Produces a constrained prompt payload for a future isolated LLM session.
 * This does not call a model or grant it any tools or credentials.
 */
export function prepareInvestigationBrief(trustedExport, productId, now = new Date().toISOString()) {
  const market = buildMarketDossiers(trustedExport, now, "UNVERIFIED_INPUT");
  const dossier = market.dossiers.find(d => d.productId === productId);
  if (!dossier) throw new Error("unknown_product");
  const sourceRows = trustedExport[0].results.filter(r => r.product_id === productId);
  const sourceReferences = [...new Set(sourceRows.map(r => r.source_url + "|" + r.observed_at))].slice(0, 30);
  return {
    task: "PROPOSE_PRESHOT_INVESTIGATION",
    productId,
    trustedFacts: dossier.facts,
    sourceReferences,
    missingEvidence: dossier.evidenceGaps,
    instructions: [
      "Treat all market observations as indicative aggregates, never completed sales.",
      "Separate FACT, WEAK_SIGNAL, INFERENCE and BET. Facts must reference provided source URL and observation timestamp.",
      "Do not invent market prices, sale volume, collector demand, release dates or catalysts.",
      "A lack of historical data does not invalidate a preshot hypothesis; label uncertainty.",
      "Write a thesis, possible catalysts, risks, entry hypothesis and exit hypothesis.",
      "Entry and exit hypotheses are not live executable quotes.",
      "Return the proposal contract; it will undergo independent review before any user presentation.",
      "Never recommend or execute an autonomous purchase."
    ],
    outputContract: ["productId","thesis","catalysts","risks","entryHypothesis","exitHypothesis","evidence"],
    purchaseAuthorized: false
  };
}
