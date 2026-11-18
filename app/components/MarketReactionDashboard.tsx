import Link from "next/link";
import { getTcgMarketSnapshot } from "../lib/market-data";
import { LeboncoinWatchPanel } from "./LeboncoinWatchPanel";
import { CardLiquidityPanel } from "./CardLiquidityPanel";
import { DataLimit, EvidenceGuide } from "./EvidenceGuide";

export async function MarketReactionDashboard() {
  const snapshot = await getTcgMarketSnapshot();
  const formatDate = (value: string) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" }).format(new Date(value)) : "Non disponible";
  return <div className="native-dashboard">
    <section className="dashboard-hero">
      <div><p className="native-eyebrow">EDGE / MARKET REACTION INTELLIGENCE</p><h1>Comprendre ce qui fait bouger les TCG.</h1><p className="dashboard-subtitle">Relier les publications, les changements d’offre, les prix et les réactions — sans confondre corrélation et causalité.</p></div>
      <div className="dashboard-stamp"><span className={snapshot.status === "OK" ? "status-dot good" : "status-dot warn"} />COUVERTURE {snapshot.status}</div>
    </section>
    <section className="dashboard-metrics" aria-label="Couverture de l'intelligence de marché">
      <div className="dashboard-metric"><span>Lignes de cartes observées</span><strong>{snapshot.cards.length}</strong><small>Présentes dans le relevé courant, pas nécessairement uniques.</small></div>
      <div className="dashboard-metric"><span>Dossiers de réaction TCG</span><strong>{snapshot.reactionCaseCount}</strong><small>Cas référencés, pas forcément assez documentés pour conclure.</small></div>
      <div className="dashboard-metric"><span>Éléments de publication reliés</span><strong>{snapshot.publishedEventCount}</strong><small>Références recensées, sans causalité démontrée.</small></div>
      <div className="dashboard-metric"><span>Ventes conclues signalées</span><strong>{snapshot.completedSales}</strong><small>Déclarées dans les données, preuves à examiner au cas par cas.</small></div>
    </section>
    {snapshot.warning && <div className="dashboard-warning" role="status">{snapshot.warning}</div>}
    <LeboncoinWatchPanel />
    <CardLiquidityPanel />
    <section className="dashboard-section">
      <div className="dashboard-section-heading"><div><p className="native-eyebrow">ÉTAT DES PREUVES</p><h2>Réactions TCG documentées</h2></div><span className="dashboard-date">Dernier relevé : {formatDate(snapshot.observedAt)}</span></div>
      {snapshot.reactionCases.length > 0 && <div className="edge-mri-cases">
        <p className="native-eyebrow">DOSSIERS MRI · SOURCES RÉFÉRENCÉES</p>
        {snapshot.reactionCases.map(item => <article className="edge-mri-case" key={item.productId}>
          <div><span className="edge-product-kicker">{item.productId.replaceAll("_", " ").toUpperCase()}</span><h3>{item.publicationCount} publication{item.publicationCount === 1 ? "" : "s"} référencée{item.publicationCount === 1 ? "" : "s"}</h3><p>Réaction : {item.reactionStatus} · Décision financière : {item.financialDecision}</p></div>
          {item.publications.length > 0 && <details><summary>Voir les publications ({item.publications.length})</summary><ul>{item.publications.map((publication, index) => <li key={index}><a href={publication.url} target="_blank" rel="noopener noreferrer">{publication.title}</a><small> {publication.publishedAt ? publication.publishedAt.slice(0,10) : "Date inconnue"} · Relation : {publication.relationship}</small></li>)}</ul></details>}
          {item.productId.startsWith("pokemon_card_") && snapshot.cards.some(card => card.productId === item.productId) && <Link href={`/explorer/${encodeURIComponent(item.productId)}`} className="edge-product-open">Voir la fiche produit →</Link>}
        </article>)}
      </div>}
      {snapshot.reactionCaseCount > 0 ? <div className="dashboard-empty">Des dossiers Pokémon sont référencés. Les publications ci-dessus sont des références documentaires, pas des preuves de causalité ou d'achat.</div> : <div className="mri-empty-state">
        <span className="mri-empty-symbol">⌁</span>
        <h3>Aucun dossier de réaction TCG vérifiable dans le dernier relevé.</h3>
        <p>Les données disponibles permettent de relever quelques prix indicatifs, mais pas encore de relier un événement à une réaction mesurée sur le marché TCG.</p>
      </div>}
    </section>
    <section className="dashboard-method">
      <p className="native-eyebrow">MÉTHODE D'ANALYSE</p><h2>Ce qu'EDGE doit réunir avant de conclure.</h2>
      <div className="method-grid">
        <div><strong>1 · Situation avant l'événement</strong><p>Historique horodaté des prix, de l'offre, de la disponibilité et des ventes réalisées.</p></div>
        <div><strong>2 · Catalyseur documenté</strong><p>Publication officielle, annonce de réimpression, précommande, retrait, rupture ou action d'un acteur identifié.</p></div>
        <div><strong>3 · Réaction après l'événement</strong><p>Mesures à plusieurs horizons, comparaisons indépendantes et séparation stricte entre corrélation et causalité.</p></div>
      </div>
    </section>
    <EvidenceGuide compact />
    <section className="dashboard-method">
      <p className="native-eyebrow">LIMITES ACTUELLES</p><h2>Ne pas surinterpréter deux prix.</h2>
      <DataLimit>Les relevés TCG présents sont des indications agrégées, sans preuve de transaction, avec disponibilité et langue non confirmées. Aucun score de hype, de liquidité ou de probabilité de hausse ne doit être calculé à partir de ce seul échantillon.</DataLimit>
    </section>
    <footer className="native-footer">EDGE · Les faits, signaux faibles, inférences et paris doivent rester distincts. Fiabilité non vérifiée lorsque les preuves sont insuffisantes.</footer>
  </div>;
}
