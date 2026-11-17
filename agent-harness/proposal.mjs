// EDGE agent output contract. This file deliberately has no network or write privileges.
const MAX_TEXT = 2000;
const required = ["productId", "thesis", "catalysts", "risks", "entryHypothesis", "exitHypothesis", "evidence"];
const plain = (value) => typeof value === "string" && value.trim().length > 0 && value.length <= MAX_TEXT;
const allowedKind = new Set(["FACT", "WEAK_SIGNAL", "INFERENCE", "BET"]);
export function validateProposal(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("invalid_proposal");
  for (const key of required) if (!(key in input)) throw new Error("missing_" + key);
  if (!plain(input.productId) || !/^[a-zA-Z0-9_-]{1,120}$/.test(input.productId)) throw new Error("invalid_product");
  for (const key of ["thesis", "entryHypothesis", "exitHypothesis"]) if (!plain(input[key])) throw new Error("invalid_" + key);
  for (const key of ["catalysts", "risks"]) {
    if (!Array.isArray(input[key]) || input[key].length < 1 || input[key].length > 12 || !input[key].every(plain)) throw new Error("invalid_" + key);
  }
  if (!Array.isArray(input.evidence) || input.evidence.length < 1 || input.evidence.length > 24) throw new Error("invalid_evidence");
  const evidence = input.evidence.map((item) => {
    if (!item || typeof item !== "object" || !allowedKind.has(item.kind) || !plain(item.claim)) throw new Error("invalid_evidence_item");
    if (item.kind === "FACT") {
      if (!plain(item.sourceUrl) || !/^https:\/\//.test(item.sourceUrl) || !plain(item.observedAt) || Number.isNaN(Date.parse(item.observedAt))) throw new Error("unverified_fact");
    }
    if (item.sourceUrl !== undefined && (!plain(item.sourceUrl) || !/^https:\/\//.test(item.sourceUrl))) throw new Error("invalid_source");
    return { kind: item.kind, claim: item.claim, ...(item.sourceUrl ? { sourceUrl: item.sourceUrl } : {}), ...(item.observedAt ? { observedAt: item.observedAt } : {}) };
  });
  return Object.freeze({
    productId: input.productId,
    thesis: input.thesis,
    catalysts: [...input.catalysts],
    risks: [...input.risks],
    entryHypothesis: input.entryHypothesis,
    exitHypothesis: input.exitHypothesis,
    evidence,
    status: "PROPOSAL_REQUIRES_HUMAN_REVIEW",
    marketDataVerified: false,
    purchaseAuthorized: false
  });
}
