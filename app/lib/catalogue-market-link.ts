import { catalogueVariant, marketVariant, compareVariants, isCatalogueLanguage } from "./product-variant";
import type { TcgCard } from "./market-data";

export type CatalogueMarketLink =
  | { status: "NO_MATCH"; productId: null; card: null }
  | { status: "CANDIDATE_UNVERIFIED"; productId: string; card: TcgCard; variant: ReturnType<typeof marketVariant> };

/**
 * Exact catalogue ID -> EDGE legacy ID. This is an identity candidate,
 * NOT proof of card edition, condition, grade or a completed sale.
 */
export function legacyPokemonProductId(cardId: string): string | null {
  const match = /^([a-zA-Z0-9]+)-([0-9]+)$/.exec(cardId);
  if (!match) return null;
  return `pokemon_card_${match[1]}_${match[2]}`;
}

export function filterCatalogueSaleVariants<T extends { key: string }>(
  cardId: string, language: string, variants: readonly T[],
): T[] {
  if (!isCatalogueLanguage(language)) return [];
  return variants.filter(({ key }) => {
    const [reference, saleLanguage] = key.split(":");
    return reference === cardId && saleLanguage === language;
  });
}

export function linkCatalogueToMarket(
  cardId: string,
  language: string,
  cards: readonly TcgCard[],
): CatalogueMarketLink {
  const productId = legacyPokemonProductId(cardId);
  if (!productId || !isCatalogueLanguage(language)) return { status: "NO_MATCH", productId: null, card: null };
  const target = catalogueVariant(language);
  const compatible = cards
    .filter(card => card.productId === productId || card.productId === `pokemon_card_${cardId}`)
    .map(card => ({ card, variant: card.variant ?? marketVariant() }))
    .filter(({ variant }) => compareVariants(target, variant) !== "CONFLICT");
  const exactLanguage = compatible.filter(({ variant }) => variant.language.value === language);
  const matches = exactLanguage.length ? exactLanguage : compatible;
  if (matches.length !== 1) return { status: "NO_MATCH", productId: null, card: null };
  const { card, variant } = matches[0];
  return { status: "CANDIDATE_UNVERIFIED", productId: card.productId, card, variant };
}
