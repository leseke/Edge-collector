/**
 * PRODUCT-002C — explicit, provenance-aware card variant dimensions.
 * UNKNOWN is not evidence of a default/standard edition or an ungraded card.
 * This module classifies evidence; it never guesses from a catalogue name.
 */
export type EvidenceValue<T extends string> =
  | { status: "UNKNOWN"; value: null; source: null }
  | { status: "VERIFIED"; value: T; source: string };

export const catalogueLanguages = { fr: "Français", en: "Anglais", ja: "Japonais", it: "Italien" } as const;
type CatalogueLanguage = keyof typeof catalogueLanguages;
type MarketLanguage = CatalogueLanguage | "de" | "es";

export function isCatalogueLanguage(value: string): value is CatalogueLanguage {
  return Object.hasOwn(catalogueLanguages, value);
}

export type ProductVariant = {
  language: EvidenceValue<MarketLanguage>;
  edition: EvidenceValue<"FIRST_EDITION" | "UNLIMITED" | "OTHER">;
  condition: EvidenceValue<"NM" | "EX" | "GD" | "PL" | "PO">;
  grading: EvidenceValue<"RAW" | "PSA" | "BGS" | "CGC" | "OTHER">;
  grade: EvidenceValue<string>;
};

const unknown = <T extends string>(): EvidenceValue<T> => ({ status: "UNKNOWN", value: null, source: null });

export function catalogueVariant(language: string): ProductVariant {
  return {
    language: isCatalogueLanguage(language)
      ? { status: "VERIFIED", value: language, source: "TCGdex catalogue locale" }
      : unknown(),
    edition: unknown(), condition: unknown(), grading: unknown(), grade: unknown(),
  };
}

function readEvidence<T extends string>(
  input: unknown,
  isValue: (value: string) => value is T,
): EvidenceValue<T> {
  if (!input || typeof input !== "object") return unknown();
  const { value, source } = input as { value?: unknown; source?: unknown };
  if (typeof value !== "string" || !isValue(value) || typeof source !== "string") return unknown();
  try {
    const url = new URL(source);
    if (url.protocol === "https:" && !url.username && !url.password) {
      return { status: "VERIFIED", value, source: url.href };
    }
  } catch {
    return unknown();
  }
  return unknown();
}

export function marketVariant(input?: unknown): ProductVariant {
  // The legacy market_language_verified flag does not identify a language.
  const evidence = input && typeof input === "object" ? input as Record<string, unknown> : {};
  const grading = readEvidence(evidence.grading, (value): value is "RAW" | "PSA" | "BGS" | "CGC" | "OTHER" =>
    /^(RAW|PSA|BGS|CGC|OTHER)$/.test(value));
  return {
    language: readEvidence(evidence.language, (value): value is MarketLanguage => /^(fr|en|ja|it|de|es)$/.test(value)),
    edition: readEvidence(evidence.edition, (value): value is "FIRST_EDITION" | "UNLIMITED" | "OTHER" =>
      /^(FIRST_EDITION|UNLIMITED|OTHER)$/.test(value)),
    condition: readEvidence(evidence.condition, (value): value is "NM" | "EX" | "GD" | "PL" | "PO" =>
      /^(NM|EX|GD|PL|PO)$/.test(value)),
    grading,
    grade: grading.status === "VERIFIED" && grading.value !== "RAW"
      ? readEvidence(evidence.grade, (value): value is string => /^(?:[1-9](?:\.5)?|10)$/.test(value))
      : unknown(),
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
