import { summarizeCardLiquidity, type CardLiquidityEvidence } from "../lib/card-liquidity";
import { RadarSaleCard } from "./RadarSaleCard";

const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function CardLiquidityPanel({ cards, scan }: {
  cards: CardLiquidityEvidence[];
  scan: { scan_day: string; status: string } | null;
}) {
  const asOf = new Date().toISOString().slice(0, 10);
  const cases = cards.map(card => ({ card, facts: summarizeCardLiquidity(card, asOf) }));
  const ranked = cases.filter(({ facts }) => facts.signal === "SUPPLY_TIGHTENING");
  return <section aria-label="Fréquence des ventes par variante">
    {scan && <p>Dernier relevé le {date.format(new Date(scan.scan_day))}.</p>}
    <p className="radar-sales-description">Les chiffres portent sur les annonces et les ventes documentées par EDGE.</p>
    <ul className="radar-sales radar-liquidity">
      {[...ranked, ...cases.filter(({ facts }) => facts.signal !== "SUPPLY_TIGHTENING")].map(({ card, facts }) => {
        const { key, name, variant } = card;
        const last90Days = facts.saleWindows.find(window => window.days === 90)?.observed ?? 0;
        return <li key={key}>
          {facts.lastPaid ? <RadarSaleCard sale={{ ...facts.lastPaid, key, name, variant }} /> : <h3>{name} · {variant}</h3>}
          <div className="radar-liquidity-facts">
            <span>{last90Days === 0 ? "Aucune vente documentée sur 90 jours" :
              `${last90Days} vente${last90Days > 1 ? "s" : ""} sur 90 jours`}</span>
            <span>{facts.active === null ? "Annonces actives non relevées" :
              `${facts.active} annonces observées le ${date.format(new Date(facts.listingDay!))}`}</span>
            {facts.change !== null && <span>Variation des annonces observées {facts.change > 0 ? "+" : ""}{facts.change}</span>}
            {facts.signal === "SUPPLY_TIGHTENING" && <span>À suivre · L’offre observée baisse et les prix payés se maintiennent ou montent.</span>}
          </div>
        </li>;
      })}
    </ul>
  </section>;
}
