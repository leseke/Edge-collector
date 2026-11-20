import { leboncoinSearchUrl, leboncoinWatch } from "../lib/leboncoin-watch";

export function LeboncoinWatchPanel({ offersUrl = null }: { offersUrl?: string | null }) {
  return <section id="analyse-annonce" className="dashboard-section radar-section" aria-labelledby="leboncoin-watch-title">
    <h2 id="leboncoin-watch-title" className="radar-section-title" data-tone="gold">Surveillance Leboncoin</h2>
    <p className="radar-sales-description">EDGE prépare l’importation automatique des alertes reçues dans Outlook. Tu n’as plus besoin de saisir un lien d’annonce : les offres seront intégrées au radar lorsque la connexion et la collecte seront activées.</p>
    <div className="radar-data-pending" role="status">
      <strong>{offersUrl ? "Consultation des offres collectées" : "Source Outlook non reliée à cette interface"}</strong>
      <p>{offersUrl ?
        "Ouvre la consultation privée pour voir les annonces réellement enregistrées. La disponibilité et le prix actuel devront encore être vérifiés sur Leboncoin." :
        "Les annonces apparaîtront dans une vue privée lorsque la connexion au Worker et l’importation Outlook auront été autorisées. Aucune annonce fictive n’est affichée."}</p>
      {offersUrl && <a className="radar-action primary" href={offersUrl} target="_blank" rel="noopener noreferrer">Voir les offres importées ↗</a>}
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
