export type PurchaseBasis = { kind: "auction" | "fixed"; cents: number | null };

export function amountInCents(input: string): number | null {
  const match = /^(\d{1,10})(?:[,.](\d{1,2}))?$/.exec(input.trim());
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

export function deliveredCost(price: number | null, fees: string, shipping: string) {
  const buyerFees = amountInCents(fees);
  const transport = amountInCents(shipping);
  if (price === null || !Number.isSafeInteger(price) || price <= 0 || buyerFees === null || transport === null) return null;
  const total = price + buyerFees + transport;
  return Number.isSafeInteger(total) ? total : null;
}
