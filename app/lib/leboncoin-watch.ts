export const leboncoinWatch = [
  "cartes Pokémon",
  "cartes Pokémon Tempête Argentée",
  "Pokémon 30 ans",
  "Pokémon 25 ans",
  "Pokémon ME6",
  "Pokémon Héros Transcendants",
] as const;

export function leboncoinSearchUrl(query: string) {
  return "https://www.leboncoin.fr/recherche?" + new URLSearchParams({ text: query });
}
