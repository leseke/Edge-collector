export type PurchaseBasis = { kind: "auction" | "fixed"; cents: number | null };

// GCC Vault, one item sent by Colissimo. Source: https://gradedcardcenter.com/tarifs
export const colissimoStartingCents = 1200;

export function estimateDeliveredCost(price: number | null) {
  if (price === null || price <= 0 || !Number.isSafeInteger(price)) return null;
  const insurance = Math.round(price / 100);
  const estimate = price + colissimoStartingCents + insurance;
  return Number.isSafeInteger(estimate) ? { insurance, estimate } : null;
}
