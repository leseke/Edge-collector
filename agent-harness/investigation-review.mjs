import { validateProposal } from "./proposal.mjs";
import { buildMarketDossiers } from "./market-dossier.mjs";

/**
 * A model can propose a preshot thesis, but cannot authenticate its own facts.
 * FACT claims must cite a URL and timestamp present in the trusted D1 export.
 * Other statements remain explicit hypotheses, not market-verified evidence.
 */
export function reviewInvestigation(rawProposal, trustedExport, now = new Date().toISOString()) {
  const proposal = validateProposal(rawProposal);
  const market = buildMarketDossiers(trustedExport, now, "UNVERIFIED_INPUT");
  const dossier = market.dossiers.find(d => d.productId === proposal.productId);
  if (!dossier) throw new Error("product_not_in_trusted_snapshot");
  const rows = trustedExport[0].results.filter(r => r.product_id === proposal.productId);
  const trustedSources = new Set(rows.map(r => r.source_url + "|" + r.observed_at));
  const supportedFacts = [];
  const unsupportedFacts = [];
  for (const item of proposal.evidence.filter(e => e.kind === "FACT")) {
    if (trustedSources.has(item.sourceUrl + "|" + item.observedAt)) supportedFacts.push(item);
    else unsupportedFacts.push(item);
  }
  const hypotheses = proposal.evidence.filter(e => e.kind !== "FACT");
  const claims = {
    factsWithMatchingCitation: supportedFacts,
    unsupportedFacts,
    weakSignals: hypotheses.filter(e => e.kind === "WEAK_SIGNAL"),
    inferences: hypotheses.filter(e => e.kind === "INFERENCE"),
    bets: hypotheses.filter(e => e.kind === "BET"),
  };
  return {
    schemaVersion: 1,
    productId: proposal.productId,
    status: unsupportedFacts.length ? "NEEDS_EVIDENCE_CORRECTION" : "PROPOSAL_REQUIRES_HUMAN_REVIEW",
    thesis: proposal.thesis,
    catalysts: proposal.catalysts,
    risks: [...new Set([...dossier.risks, ...proposal.risks])],
    entryHypothesis: proposal.entryHypothesis,
    exitHypothesis: proposal.exitHypothesis,
    evidence: claims,
    observedMarket: dossier.facts,
    evidenceGaps: dossier.evidenceGaps,
    provenance: market.provenance,
    sourceContext: market.sourceContext,
    citationMetadataMatched: unsupportedFacts.length === 0 && supportedFacts.length > 0,
    claimSemanticsVerified: false,
    demandConfirmed: false,
    completedSalesConfirmed: false,
    purchaseAuthorized: false,
  };
}
