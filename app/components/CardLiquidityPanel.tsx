import { reviewedCardLiquidity, summarizeCardLiquidity } from "../lib/card-liquidity";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function CardLiquidityPanel() {
  const asOf = new Date().toISOString().slice(0, 10);
  return <section className="dashboard-section" aria-label="Offre et liquidité">
    <h2>Offre et liquidité des cartes</h2>
    {reviewedCardLiquidity.map(card => {
      const facts = summarizeCardLiquidity(card, asOf);
      return <article key={card.name + card.variant} className="edge-mri-case">
        <div>
          <h3>{card.name}</h3>
          <p>{card.variant} · <a href={card.releaseSource}>Sortie le {date.format(new Date(card.releasedOn))}</a> · {facts.ageDays} jours</p>
          <p>{facts.active === null ? "Pas de relevé comparable d’annonces actives" :
            `${facts.active} annonces observées le ${date.format(new Date(facts.listingDay!))}`}</p>
          {facts.change !== null && <p>Évolution sur le même périmètre {facts.change > 0 ? "+" : ""}{facts.change} · {facts.newlyObserved} absentes du relevé précédent</p>}
          <p>Ventes payées documentées · {facts.saleWindows.map(window => `${window.days} j : ${window.observed}`).join(" · ")}</p>
          {facts.lastPaid && <p>Dernière vente documentée · {euros.format(facts.lastPaid.cents / 100)} · <a href={facts.lastPaid.source}>{date.format(new Date(facts.lastPaid.day))}</a></p>}
          <small>Couverture partielle. Le taux de drop reste inconnu sans données d’ouverture.</small>
        </div>
      </article>;
    })}
  </section>;
}
