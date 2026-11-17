import test from "node:test";
import assert from "node:assert/strict";
import { validateProposal } from "../proposal.mjs";
const proposal = () => ({
  productId: "pokemon_card_base1_4",
  thesis: "Potential asymmetric demand hypothesis, not established",
  catalysts: ["Anniversary interest could increase"],
  risks: ["Reprints could reduce scarcity"],
  entryHypothesis: "Watch for a price below verified historical ranges",
  exitHypothesis: "Review after 12 months; no guaranteed return",
  evidence: [{ kind: "WEAK_SIGNAL", claim: "Unconfirmed demand change" }]
});
test("unverified opportunity remains a non-executable proposal", () => {
  const output = validateProposal(proposal());
  assert.equal(output.status, "PROPOSAL_REQUIRES_HUMAN_REVIEW");
  assert.equal(output.purchaseAuthorized, false);
  assert.equal(output.marketDataVerified, false);
});
test("facts require provenance and observation timestamp", () => {
  const input = proposal();
  input.evidence = [{ kind: "FACT", claim: "Observed price" }];
  assert.throws(() => validateProposal(input), /unverified_fact/);
  input.evidence[0].sourceUrl = "https://api.tcgdex.net/v2/fr/cards/base1-4";
  input.evidence[0].observedAt = "2026-11-17T12:00:00Z";
  assert.equal(validateProposal(input).evidence[0].kind, "FACT");
});
test("rejects fabricated confidence and unsafe proposal shapes", () => {
  const input = proposal();
  input.catalysts = [];
  assert.throws(() => validateProposal(input), /invalid_catalysts/);
  assert.throws(() => validateProposal({}), /missing_productId/);
});
