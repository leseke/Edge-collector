import { catalogueVariant, marketVariant, compareVariants } from "./product-variant";
import type { TcgCard } from "./market-data";

export type CatalogueMarketLink =
  | { status: "NO_MATCH"; productId: null; card: null }
  | { status: "CANDIDATE_UNVERIFIED"; productId: string; card: TcgCard };

/**
 * Exact catalogue ID -> EDGE legacy ID. This is an identity candidate,
 * NOT proof of card edition, condition, grade or a completed sale.
 */
export function legacyPokemonProductId(cardId: string): string | null {
  const match = /^([a-zA-Z0-9]+)-([0-9]+)$/.exec(cardId);
  if (!match) return null;
  return `pokemon_card_${match[1]}_${match[2]}`;
}

export function linkCatalogueToMarket(
  cardId: string,
  language: string,
  cards: readonly TcgCard[],
): CatalogueMarketLink {
  const productId = legacyPokemonProductId(cardId);
  if (!productId || !["fr", "en", "ja"].includes(language)) return { status: "NO_MATCH", productId: null, card: null };
  const matches = cards.filter(card => card.productId === productId);
  // Fail closed if the market snapshot contains ambiguous duplicate identities.
  if (matches.length !== 1) return { status: "NO_MATCH", productId: null, card: null };
  const card = matches[0];
  if (compareVariants(catalogueVariant(language), marketVariant(card.languageVerified)) === "CONFLICT") return { status: "NO_MATCH", productId: null, card: null };
  return { status: "CANDIDATE_UNVERIFIED", productId, card };
}
