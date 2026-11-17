/**
 * PRODUCT-002C — explicit, provenance-aware card variant dimensions.
 * UNKNOWN is not evidence of a default/standard edition or an ungraded card.
 * This module classifies evidence; it never guesses from a catalogue name.
 */
export type EvidenceValue<T extends string> =
  | { status: "UNKNOWN"; value: null; source: null }
  | { status: "VERIFIED"; value: T; source: string };

export type ProductVariant = {
  language: EvidenceValue<"fr" | "en" | "ja">;
  edition: EvidenceValue<"FIRST_EDITION" | "UNLIMITED" | "OTHER">;
  condition: EvidenceValue<"NM" | "EX" | "GD" | "PL" | "PO">;
  grading: EvidenceValue<"RAW" | "PSA" | "BGS" | "CGC" | "OTHER">;
  grade: EvidenceValue<string>;
};

const unknown = <T extends string>(): EvidenceValue<T> => ({ status: "UNKNOWN", value: null, source: null });

export function catalogueVariant(language: string): ProductVariant {
  return {
    language: ["fr", "en", "ja"].includes(language)
      ? { status: "VERIFIED", value: language as "fr" | "en" | "ja", source: "TCGdex catalogue locale" }
      : unknown(),
    edition: unknown(), condition: unknown(), grading: unknown(), grade: unknown(),
  };
}

export function marketVariant(_languageVerified: boolean): ProductVariant {
  // The legacy flag says verification happened, but does not encode WHICH language.
  // Never infer FR from the flag alone.
  return {
    language: unknown(),
    edition: unknown(), condition: unknown(), grading: unknown(), grade: unknown(),
  };
}

export function compareVariants(catalogue: ProductVariant, market: ProductVariant):
  "CONFLICT" | "PARTIAL" | "VERIFIED" {
  let incomplete = false;
  for (const key of ["language", "edition", "condition", "grading", "grade"] as const) {
    const a = catalogue[key], b = market[key];
    if (a.status === "VERIFIED" && b.status === "VERIFIED" && a.value !== b.value) return "CONFLICT";
    if (a.status === "UNKNOWN" || b.status === "UNKNOWN") incomplete = true;
  }
  return incomplete ? "PARTIAL" : "VERIFIED";
}
