import { getTcgMarketSnapshot, type TcgCard } from "../lib/market-data";

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
      <p className="tcg-caveat">Ce montant est une indication de prix, pas une vente conclue. Variante, langue et état exacts non confirmés.</p>
    </div>
  </article>;
}
export async function MarketDashboard() {
  const snapshot = await getTcgMarketSnapshot();
  const freshDate = snapshot.observedAt ? date(snapshot.observedAt) : "Non disponible";
  return <div className="native-dashboard">
    <section className="dashboard-hero">
      <div><p className="native-eyebrow">EDGE / VOTRE ESPACE</p><h1>Repérer les opportunités avant le consensus.</h1><p className="dashboard-subtitle">Un point de départ pour explorer les produits suivis, leurs prix observés et les informations qui restent à vérifier.</p></div>
      <div className="dashboard-stamp"><span className={snapshot.status === "OK" ? "status-dot good" : "status-dot warn"} />DONNÉES {snapshot.status === "OK" ? "DISPONIBLES" : snapshot.status === "PARTIAL" ? "PARTIELLES" : "LIMITÉES"}</div>
    </section>
    <section className="dashboard-metrics" aria-label="État des données">
      <div className="dashboard-metric"><span>Produits observés</span><strong>{snapshot.cards.length}</strong><small>Produits actuellement visibles dans EDGE.</small></div>
      <div className="dashboard-metric"><span>Relevés exploitables</span><strong>{snapshot.successfulCount}</strong><small>Données reçues et utilisables.</small></div>
      <div className="dashboard-metric"><span>Relevés incomplets</span><strong>{snapshot.failedCount}</strong><small>Informations indisponibles ou incomplètes.</small></div>
      <div className="dashboard-metric"><span>Ventes documentées</span><strong>0</strong><small>Transactions identifiées dans les données.</small></div>
    </section>
    <section className="dashboard-section">
      <div className="dashboard-section-heading"><div><p className="native-eyebrow">PRODUITS À EXPLORER</p><h2>Marché observé</h2></div><span className="dashboard-date">Dernier relevé : {freshDate}</span></div>
      {snapshot.warning && <div className="dashboard-warning" role="status">{snapshot.warning}</div>}
      {snapshot.cards.length ? <div className="tcg-card-grid">{snapshot.cards.map((card) => <CardTile key={card.productId} card={card} />)}</div> : <div className="dashboard-empty">Aucun produit vérifiable pour le moment. Les prochaines observations apparaîtront ici.</div>}
    </section>
    <section className="dashboard-method">
      <p className="native-eyebrow">COMMENT LIRE CES PRIX</p>
      <h2>Observer n'est pas acheter.</h2>
      <div className="method-grid">
        <div><strong>Prix affiché ≠ prix vendu</strong><p>Une annonce ou une moyenne indicative ne prouve pas qu'un acheteur a payé ce montant.</p></div>
        <div><strong>Produit exact à confirmer</strong><p>Langue, édition, état et disponibilité peuvent modifier fortement la valeur réelle.</p></div>
        <div><strong>Une piste n'est pas une certitude</strong><p>EDGE peut signaler un pari précoce, mais conserve les risques et les preuves manquantes.</p></div>
      </div>
      <a className="edge-analysis-link" href="/mri">Comprendre les signaux de marché →</a>
    </section>
    <footer className="native-footer">EDGE · Données observées séparées des estimations · Aucun achat ni rendement futur n’est validé par cette interface.</footer>
  </div>;
}
