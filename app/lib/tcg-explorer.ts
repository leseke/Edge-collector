import type { TcgCard } from "./market-data";
export type ExplorerSort = "name" | "low" | "high";
const normalize = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase("fr");
export function filterCards(cards: readonly TcgCard[], query: string, series: string, sort: ExplorerSort) {
  const terms = normalize(query.trim()).split(/\s+/).filter(Boolean);
  const result = cards.filter(card => (!series || card.setName === series) && terms.every(term =>
    normalize([card.name,card.setName,card.number,card.rarity,card.productId].join(" ")).includes(term)));
  return result.sort((a,b) => {
    if (sort !== "name") {
      const ap = a.low !== null && Number.isFinite(a.low) && a.low > 0;
      const bp = b.low !== null && Number.isFinite(b.low) && b.low > 0;
      if (ap !== bp) return ap ? -1 : 1;
      if (ap && bp) {
        const currency = a.currency.localeCompare(b.currency);
        if (currency) return currency;
        const delta = (a.low! - b.low!) * (sort === "low" ? 1 : -1);
        if (delta) return delta;
      }
    }
    return a.name.localeCompare(b.name,"fr") || a.productId.localeCompare(b.productId);
  });
}
