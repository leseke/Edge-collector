import { leboncoinSearchUrl, leboncoinWatch } from "../lib/leboncoin-watch";

export function LeboncoinWatchPanel() {
  return <section id="analyse-annonce" className="dashboard-section radar-section" aria-labelledby="leboncoin-watch-title">
    <h2 id="leboncoin-watch-title" className="radar-section-title" data-tone="gold">Surveillance Leboncoin</h2>
    <p className="radar-sales-description">EDGE prépare l’importation automatique des alertes reçues dans Outlook. Tu n’as plus besoin de saisir un lien d’annonce : les offres seront intégrées au radar lorsque la connexion et la collecte seront activées.</p>
    <div className="radar-data-pending" role="status">
      <strong>Collecte Outlook non activée</strong>
      <p>Aucune annonce n’est présentée comme collectée tant qu’une importation réelle n’a pas été vérifiée. Les prix signalés dans des emails restent des offres non vérifiées, jamais des ventes conclues.</p>
    </div>
    <details className="radar-disclosure">
      <summary>Recherches surveillées sur Leboncoin</summary>
      <ul>{leboncoinWatch.map(query => <li key={query}>
        <a href={leboncoinSearchUrl(query)} target="_blank" rel="noopener noreferrer">{query} ↗</a>
      </li>)}</ul>
      <p>Ces liens ouvrent les recherches publiques ; ils ne constituent pas un historique de collecte.</p>
    </details>
  </section>;
}
