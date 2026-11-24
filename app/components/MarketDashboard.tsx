import { TcgExplorer } from "./TcgExplorer";
import { getTcgMarketSnapshot, type TcgCard, type CommercialRow } from "../lib/market-data";
import { EvidenceGuide } from "./EvidenceGuide";
import { TcgCorpusDownload } from "./TcgCorpusDownload";

function date(value: string): string {
  if (!value) return "Date non disponible";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Date non disponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" }).format(parsed);
}
function money(value: number | null, currency: string): string {
  if (value === null || !Number.isFinite(value)) return "Non établi";
  if (!/^[A-Z]{3}$/.test(currency)) return `${value} (devise inconnue)`;
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}
function CardTile({ card, commercial }: { card: TcgCard; commercial: CommercialRow[] }) {
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
      <div className="tcg-source-row"><span>Source déclarée : {card.source}</span><span>{card.availability === "UNKNOWN" ? "Disponibilité inconnue" : card.availability}</span></div>
      <div className="tcg-source-row"><span>Relevé : {date(card.observedAt)}</span><span>{card.languageVerified ? "Langue vérifiée" : "Langue non vérifiée"}</span></div>
      <div className="tcg-source-row"><span>Nature du prix : {card.priceKind || "Non renseignée"}</span><span>Source mise à jour : {card.sourceUpdatedAt ? date(card.sourceUpdatedAt) : "Non disponible"}</span></div>
      <details className="tcg-evidence-details">
        <summary>Observations commerciales</summary>
        {["ASKING_PRICE","DECLARED_SALE","AGGREGATED_INDICATIVE_LOW"].map(kind => {
          const rows = commercial.filter(row => row.kind === kind);
          return <section key={kind}><h4>{kind === "ASKING_PRICE" ? "Offres observées" : kind === "DECLARED_SALE" ? "Ventes déclarées (non vérifiées)" : "Prix agrégés indicatifs"}</h4>
            {rows.length ? rows.map((row,i) => <p key={i}>{row.url ? <a href={row.url} target="_blank" rel="noopener noreferrer">{row.source}</a> : row.source} · {money(row.price,row.currency || "")} · {row.availability} · {date(row.observedAt)} · {row.status}</p>) : <p>Couverture non établie pour ce relevé.</p>}
          </section>;
        })}
        <p>Enchères : aucune couverture établie. Une offre observée ne garantit pas sa disponibilité actuelle.</p>
      </details>
      <details className="tcg-evidence-details">
        <summary>Consulter le dossier de preuves</summary>
        <dl>
          <dt>Identifiant du produit</dt><dd>{card.productId}</dd>
          <dt>Identifiant du relevé</dt><dd>{card.snapshotId}</dd>
          <dt>SHA-256 du rapport contrôlé</dt><dd><code>{card.reportSha256}</code></dd>
          <dt>SHA-256 des données brutes contrôlées</dt><dd><code>{card.rawSha256}</code></dd>
          <dt>Source déclarée</dt><dd>{card.source || "Non renseignée"}</dd>
          <dt>Observation</dt><dd>{date(card.observedAt)}</dd>
          <dt>Mise à jour de la source</dt><dd>{card.sourceUpdatedAt ? date(card.sourceUpdatedAt) : "Non disponible"}</dd>
          <dt>Nature du prix</dt><dd>{card.priceKind || "Non renseignée"}</dd>
          <dt>Disponibilité</dt><dd>{card.availability === "UNKNOWN" ? "Non vérifiée" : card.availability}</dd>
          <dt>Langue</dt><dd>{card.languageVerified ? "Déclarée vérifiée" : "Non vérifiée"}</dd>
          <dt>Vente réalisée</dt><dd>Aucune preuve de transaction indépendante associée à cette fiche.</dd>
        </dl>
        <p>Fiabilité non vérifiée. Les empreintes attestent la concordance avec les fichiers du relevé, pas la véracité commerciale des informations. Ce dossier présente les métadonnées du relevé et non une enquête indépendante. Absence de preuve ne signifie pas absence de ventes.</p>
        <TcgCorpusDownload card={card} />
      </details>
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
      <div className="dashboard-metric"><span>Transactions déclarées dans le relevé</span><strong>{snapshot.completedSales === null ? "Non disponible" : snapshot.completedSales}</strong><small>Indicateur de source non vérifié : ne constitue pas une preuve de vente conclue. Zéro ne prouve pas une absence de transactions.</small></div>
    </section>
    <section className="dashboard-section">
      <div className="dashboard-section-heading"><div><p className="native-eyebrow">OBSERVATIONS SOURCÉES</p><h2>Cartes suivies</h2></div><span className="dashboard-date">Dernier relevé : {freshDate}</span></div>
      {snapshot.warning && <div className="dashboard-warning" role="status">{snapshot.warning}</div>}
      <TcgExplorer cards={snapshot.cards} tiles={snapshot.cards.map((card, i) => <CardTile key={i} card={card} commercial={snapshot.commercial.filter(row => row.productId === card.productId)} />)} />
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
