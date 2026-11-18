import assert from "node:assert/strict";
import test from "node:test";
import { analyzeListing, euroCents } from "../../app/lib/listing-analysis.ts";

test("parses euro cents without rounding or treating missing data as free", () => {
  assert.equal(euroCents(" 4,48 "), 448);
  assert.equal(euroCents("0"), 0);
  for (const malformed of ["", "-1", "1.001", "1e2"]) assert.equal(euroCents(malformed), null);
});
test("preserves unknown resale and fees, and clamps the asking limit to cash and gain", () => {
  const input = { askingCents: 3900, acquisitionFeesCents: 448, exitNetCents: null, targetGainCents: 0, budgetCents: 30000 };
  assert.deepEqual(analyzeListing(input), { cost: 4348, gain: null, maxAsk: null, budgetExceeded: false });
  assert.equal(analyzeListing({ ...input, acquisitionFeesCents: null, exitNetCents: 5000 }).maxAsk, null);
  assert.deepEqual(analyzeListing({ ...input, exitNetCents: 5500, targetGainCents: 800, budgetCents: 5000 }),
    { cost: 4348, gain: 1152, maxAsk: 4252, budgetExceeded: false });
  assert.equal(analyzeListing({ ...input, acquisitionFeesCents: null, budgetCents: 3899 }).budgetExceeded, true);
});
