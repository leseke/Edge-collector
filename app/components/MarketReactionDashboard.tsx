import { getTcgMarketSnapshot } from "../lib/market-data";

export async function MarketReactionDashboard() {
  const snapshot = await getTcgMarketSnapshot();
  const formatDate = (value: string) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" }).format(new Date(value)) : "Non disponible";
  return <div className="native-dashboard">
    <section className="dashboard-hero">
      <div><p className="native-eyebrow">EDGE / MARKET REACTION INTELLIGENCE</p><h1>Comprendre ce qui fait bouger les TCG.</h1><p className="dashboard-subtitle">Relier les publications, les changements d’offre, les prix et les réactions — sans confondre corrélation et causalité.</p></div>
      <div className="dashboard-stamp"><span className={snapshot.status === "OK" ? "status-dot good" : "status-dot warn"} />COUVERTURE {snapshot.status}</div>
    </section>
    <section className="dashboard-metrics" aria-label="Couverture de l'intelligence de marché">
      <div className="dashboard-metric"><span>Cartes TCG observées</span><strong>{snapshot.cards.length}</strong></div>
      <div className="dashboard-metric"><span>Dossiers de réaction TCG</span><strong>{snapshot.reactionCaseCount}</strong></div>
      <div className="dashboard-metric"><span>Événements publiés reliés</span><strong>{snapshot.publishedEventCount}</strong></div>
      <div className="dashboard-metric"><span>Ventes conclues enregistrées</span><strong>{snapshot.completedSales}</strong></div>
    </section>
    {snapshot.warning && <div className="dashboard-warning" role="status">{snapshot.warning}</div>}
    <section className="dashboard-section">
      <div className="dashboard-section-heading"><div><p className="native-eyebrow">ÉTAT DES PREUVES</p><h2>Réactions TCG documentées</h2></div><span className="dashboard-date">Dernier relevé : {formatDate(snapshot.observedAt)}</span></div>
      {snapshot.reactionCaseCount > 0 ? <div className="dashboard-empty">Des dossiers TCG sont disponibles. Leur détail sera affiché après validation des événements et des fenêtres de comparaison.</div> : <div className="mri-empty-state">
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
    <section className="dashboard-method">
      <p className="native-eyebrow">LIMITES ACTUELLES</p><h2>Ne pas surinterpréter deux prix.</h2>
      <p className="mri-limit-copy">Les relevés TCG présents sont des indications agrégées, sans preuve de transaction, avec disponibilité et langue non confirmées. Aucun score de hype, de liquidité ou de probabilité de hausse ne doit être calculé à partir de ce seul échantillon.</p>
    </section>
    <footer className="native-footer">EDGE · Les faits, signaux faibles, inférences et paris doivent rester distincts. Fiabilité non vérifiée lorsque les preuves sont insuffisantes.</footer>
  </div>;
}
