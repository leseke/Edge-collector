import { getTcgMarketSnapshot, type TcgCard } from "../lib/market-data";
import { EvidenceGuide } from "./EvidenceGuide";

function date(value: string): string {
  if (!value) return "Date non disponible";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Date non disponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" }).format(parsed);
}
function money(value: number | null, currency: string): string {
  if (value === null) return "Non établi";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}
function CardTile({ card }: { card: TcgCard }) {
  return <article className="tcg-card">
    <div className="tcg-card-visual">
      {card.image ? <img src={card.image} alt={`Illustration de ${card.name}`} loading="lazy" /> : <span>TCG</span>}
    </div>
    <div className="tcg-card-body">
      <div className="tcg-card-meta"><span>{card.setName}</span><span>#{card.number}</span></div>
      <h3>{card.name}</h3>
      <p className="tcg-rarity">{card.rarity}</p>
      <div className="tcg-price-label">Indication basse agrégée · Cardmarket via TCGdex</div>
      <div className="tcg-price">{money(card.low, card.currency)}</div>
      <div className="tcg-price-details">
        <span>Moyenne indicative <strong>{money(card.average, card.currency)}</strong></span>
        <span>Tendance indicative <strong>{money(card.trend, card.currency)}</strong></span>
      </div>
      <div className="tcg-source-row"><span>Source : {card.source}</span><span>{card.availability === "UNKNOWN" ? "Disponibilité inconnue" : card.availability}</span></div>
      <div className="tcg-source-row"><span>Relevé : {date(card.observedAt)}</span><span>{card.languageVerified ? "Langue vérifiée" : "Langue non vérifiée"}</span></div>
      <p className="tcg-caveat">Fiabilité non vérifiée : ce montant est une indication de prix, pas une vente conclue. Variante, langue et état exacts non confirmés.</p>
    </div>
  </article>;
}
export async function MarketDashboard() {
  const snapshot = await getTcgMarketSnapshot();
  const freshDate = snapshot.observedAt ? date(snapshot.observedAt) : "Non disponible";
  return <div className="native-dashboard">
    <section className="dashboard-hero">
      <div><p className="native-eyebrow">EDGE / TCG MARKET INTELLIGENCE</p><h1>Lire le marché avant le consensus.</h1><p className="dashboard-subtitle">Prix indicatifs, disponibilité, signaux et preuves — sans confondre annonces et transactions.</p></div>
      <div className="dashboard-stamp"><span className={snapshot.status === "OK" ? "status-dot good" : "status-dot warn"} />RELEVÉ {snapshot.status === "UNAVAILABLE" ? "INDISPONIBLE" : snapshot.status}</div>
    </section>
    <section className="dashboard-metrics" aria-label="État des données">
      <div className="dashboard-metric"><span>Lignes de cartes dans ce relevé</span><strong>{snapshot.cards.length}</strong><small>Observations affichables après contrôle d’intégrité.</small></div>
      <div className="dashboard-metric"><span>Observations reçues</span><strong>{snapshot.successfulCount}</strong><small>Réponses de collecte avec statut OK, pas des ventes.</small></div>
      <div className="dashboard-metric"><span>Observations en échec</span><strong>{snapshot.failedCount}</strong><small>Collectes non concluantes ou données non exploitables.</small></div>
      <div className="dashboard-metric"><span>Transactions déclarées dans le relevé</span><strong>{snapshot.completedSales}</strong><small>Indicateur de source non vérifié : ne constitue pas une preuve de vente conclue. Zéro ne prouve pas une absence de transactions.</small></div>
    </section>
    <section className="dashboard-section">
      <div className="dashboard-section-heading"><div><p className="native-eyebrow">OBSERVATIONS SOURCÉES</p><h2>Cartes suivies</h2></div><span className="dashboard-date">Dernier relevé : {freshDate}</span></div>
      {snapshot.warning && <div className="dashboard-warning" role="status">{snapshot.warning}</div>}
      {snapshot.cards.length ? <div className="tcg-card-grid">{snapshot.cards.map((card) => <CardTile key={card.productId} card={card} />)}</div> : <div className="dashboard-empty">Aucune observation TCG vérifiable n’est disponible dans le dernier relevé.</div>}
    </section>
    <EvidenceGuide />
    <section className="dashboard-method">
      <p className="native-eyebrow">CADRE DE LECTURE</p><h2>Ce que ces données disent — et ne disent pas.</h2>
      <div className="method-grid">
        <div><strong>Prix indicatifs</strong><p>Les valeurs issues d’agrégateurs ne sont ni des prix de vente réalisés, ni une preuve de liquidité.</p></div>
        <div><strong>Variantes à confirmer</strong><p>Langue, édition, finition, état et version exacte doivent être confirmés avant toute comparaison.</p></div>
        <div><strong>Pas de recommandation automatique</strong><p>Deux observations ne suffisent pas à établir une tendance, une rareté ou une asymétrie d’investissement.</p></div>
      </div>
    </section>
    <footer className="native-footer">EDGE · Données observées séparées des estimations · Aucun achat ni rendement futur n’est validé par cette interface.</footer>
  </div>;
}
