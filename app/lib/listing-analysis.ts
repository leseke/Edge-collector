export function euroCents(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d{1,7}(?:\.\d{1,2})?$/.test(normalized)) return null;
  const [euros, cents = ""] = normalized.split(".");
  return Number(euros) * 100 + Number(cents.padEnd(2, "0"));
}

export function analyzeListing(input: {
  askingCents: number;
  acquisitionFeesCents: number | null;
  exitNetCents: number | null;
  targetGainCents: number;
  budgetCents: number;
}) {
  const { askingCents, acquisitionFeesCents, exitNetCents, targetGainCents, budgetCents } = input;
  const cost = acquisitionFeesCents === null ? null : askingCents + acquisitionFeesCents;
  const gain = cost === null || exitNetCents === null ? null : exitNetCents - cost;
  const maxAsk = acquisitionFeesCents === null || exitNetCents === null ? null :
    Math.max(0, Math.min(budgetCents, exitNetCents - targetGainCents) - acquisitionFeesCents);
  const budgetExceeded = (cost ?? askingCents) > budgetCents;
  return { cost, gain, maxAsk, budgetExceeded };
}
