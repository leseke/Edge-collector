import { reviewedCardLiquidity, summarizeCardLiquidity } from "../lib/card-liquidity";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function CardLiquidityPanel() {
  const asOf = new Date().toISOString().slice(0, 10);
  const cases = reviewedCardLiquidity.map(card => ({ card, facts: summarizeCardLiquidity(card, asOf) }));
  const ranked = cases.filter(({ facts }) => facts.signal === "SUPPLY_TIGHTENING");
  return <section className="dashboard-section" aria-label="Offre et liquidité">
    <h2>Offre et liquidité des cartes</h2>
    {ranked.length === 0 && <p>Aucune piste de raréfaction étayée dans les relevés disponibles.</p>}
    {[...ranked, ...cases.filter(({ facts }) => facts.signal !== "SUPPLY_TIGHTENING")].map(({ card, facts }) => {
      return <article key={card.name + card.variant} className="edge-mri-case">
        <div>
          <h3>{card.name}</h3>
          {facts.signal === "SUPPLY_TIGHTENING" && <p>À approfondir · Moins d’annonces observées, ventes payées et prix médians stables ou en hausse.</p>}
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
