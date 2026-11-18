import { rankFixedOffers, type ListingPage } from "../lib/fixed-offer-ranking";
import type { SaleVariant } from "../lib/radar-paid-sales";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const price = (cents: number) => euros.format(cents / 100);
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function FixedOfferRanking({ page, variants }: { page: ListingPage; variants: SaleVariant[] }) {
  const ranked = rankFixedOffers(page.items, variants, page.checkedAt.slice(0, 10));
  return <section className="radar-comparables">
    <h4>Offres à examiner</h4>
    <p>Classement limité à la page {page.page} · {page.items.length} offres analysées.</p>
    {ranked.length === 0 ? <p>Aucun écart de prix ni signal de série identifié dans les ventes documentées pour ces offres.</p> :
      <ol>{ranked.map(row => <li key={row.item.id}>
        <a href={"#fixed-" + row.item.id}>{row.item.title}</a>
        <p>Livré estimé {price(row.cost)}{row.median !== null && <> · Médiane hors livraison {price(row.median)}</>}</p>
        {row.reason === "gap" && <p>Écart indicatif de {price(row.gap!)} sous la médiane.</p>}
        {row.reason === "series" && <p>Piste à surveiller · {row.recent} ventes de la série relevées sur 7 jours, contre {row.previous} les 7 jours précédents. La demande pour cette variante reste incertaine.</p>}
        {row.last ? <small>{row.count === 1 ? "Repère isolé" : row.count + " ventes comparables"} · Dernière vente <a href={row.last.source}>{price(row.last.cents)}</a> le {date.format(new Date(row.last.day))}.</small> :
          <small>Aucune vente payée comparable documentée.</small>}
      </li>)}</ol>}
  </section>;
}
