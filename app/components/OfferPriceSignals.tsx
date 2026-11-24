import { assessPriceDrop, resaleFeePercent } from "../lib/listing-analysis";
import type { SaleVariant } from "../lib/radar-paid-sales";
import { getPriceDrops } from "../lib/offer-price-signals";

const money = new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
const date = new Intl.DateTimeFormat("fr-FR",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Paris"});
export async function OfferPriceSignals({variants}: {variants: SaleVariant[]}) {
  const drops = await getPriceDrops();
  return <section className="dashboard-section radar-section" aria-labelledby="price-drop-title">
    <h2 id="price-drop-title">Baisses de prix observées</h2>
    <p className="radar-sales-description">Dernier relevé de chaque annonce à prix fixe, datant de moins de 48 h, comparé au précédent sur 30 jours. Une baisse ne prouve ni une sous-évaluation ni une vente.</p>
    {drops === null ? <p>Historique momentanément indisponible.</p> : drops.length === 0 ? <p>Aucune baisse récente documentée dans les relevés disponibles.</p> : drops.map(drop => {
      const assessment = assessPriceDrop({id:drop.lot_id,variantKey:drop.variant_key,cents:drop.price_cents},variants,drop.observed_at.slice(0,10));
      return <article className="edge-mri-case" key={drop.lot_id}>
      <small>SIGNAL COMMERCIAL · À INVESTIGUER</small>
      <h3>{drop.title}</h3>
      <div className="radar-sale-price"><strong>−{drop.percent.toFixed(1)} %</strong><span>{money.format(drop.previous_cents/100)} → {money.format(drop.price_cents/100)}</span></div>
      <p>{date.format(new Date(drop.previous_at))} → {date.format(new Date(drop.observed_at))}</p>
      <p>{drop.variant_key ? "Variante identifiée dans le relevé." : "Variante non confirmée."} Disponibilité actuelle à vérifier.</p>
      <div className="radar-price-comparison">
        <strong>{assessment.status === "INVESTIGATE" ? "Décote et marge théorique à investiguer" : assessment.status === "THIN_MARGIN" ? "Décote mais marge prudente insuffisante" : assessment.status === "NO_DISCOUNT" ? "Prix non inférieur à la médiane" : "Signal faible · comparables insuffisants"}</strong>
        <small>{assessment.count} ventes payées comparables sur 90 jours avant le relevé.</small>
        {assessment.median !== null && <small>Médiane : {money.format(assessment.median/100)} · marge avant frais d’achat : {money.format(assessment.headroom!/100)} (frais de revente supposés {resaleFeePercent} %).</small>}
      </div>
      <a href={drop.source} target="_blank" rel="noopener noreferrer">Vérifier l’annonce GCC ↗</a>
    </article>})}
  </section>;
}
