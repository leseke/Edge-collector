export function MarketplaceSearch({ query }: { query: string }) {
  const vinted = "https://www.vinted.fr/catalog?" + new URLSearchParams({ search_text: query });
  const leboncoin = "https://www.leboncoin.fr/recherche?" + new URLSearchParams({ text: query });
  const prompt = [
    "Recherche les annonces publiques sur Vinted France et Leboncoin pour la carte suivante : " + query + ".",
    "Vérifie le numéro de carte et l’extension. Fournis les liens directs, le prix demandé, les frais visibles, la langue, l’état ou le grade et la date de vérification.",
    "Signale les annonces inaccessibles, les informations manquantes et les résultats dont la référence diffère. Ne présente jamais un prix demandé comme une vente conclue.",
  ].join("\n");

  return (
    <section className="edge-product-panel" aria-labelledby="marketplace-search-title">
      <h2 id="marketplace-search-title">Trouver des annonces</h2>
      <p><a href={vinted} target="_blank" rel="noopener noreferrer">Rechercher sur Vinted ↗</a></p>
      <p><a href={leboncoin} target="_blank" rel="noopener noreferrer">Rechercher sur Leboncoin ↗</a></p>
      <details>
        <summary>Rechercher avec Gemini</summary>
        <p>Copie la requête ci-dessous dans Google AI Studio avec la recherche Google activée.</p>
        <textarea aria-label="Requête Gemini" readOnly rows={5} value={prompt} />
        <p><a href="https://aistudio.google.com/" target="_blank" rel="noopener noreferrer">Ouvrir Google AI Studio ↗</a></p>
      </details>
    </section>
  );
}
