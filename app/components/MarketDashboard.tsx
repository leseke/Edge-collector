import Link from "next/link";
import { AssetImage } from "./AssetImage";
import { getTcgMarketSnapshot, type TcgCard } from "../lib/market-data";

function date(value: string): string {
  if (!value) return "Date indisponible";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Date indisponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "Europe/Paris" }).format(parsed);
}
function money(value: number | null, currency: string): string {
  if (value === null) return "—";
  try { return new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 2 }).format(value); }
  catch { return "—"; }
}
function CardTile({ card }: { card: TcgCard }) {
  return <article className="edge-asset-card">
    <div className="edge-asset-art">
      <AssetImage src={card.image} name={card.name} />
      <span className="edge-asset-category">POKÉMON · CARTE</span>
    </div>
    <div className="edge-asset-content">
      <div className="edge-asset-series">{card.setName} · #{card.number}</div>
      <h3>{card.name}</h3>
      <p className="edge-asset-rarity">{card.rarity}</p>
      <div className="edge-asset-value"><span>Prix indicatif bas</span><strong>{money(card.low, card.currency)}</strong></div>
      <span className="edge-asset-uncertainty">◌ Variante et état à confirmer</span>
      <details className="edge-asset-details">
        <summary>Prix & sources <span aria-hidden="true">＋</span></summary>
        <dl>
          <div><dt>Moyenne indicative</dt><dd>{money(card.average, card.currency)}</dd></div>
          <div><dt>Tendance indicative</dt><dd>{money(card.trend, card.currency)}</dd></div>
          <div><dt>Origine</dt><dd>{card.source}</dd></div>
          <div><dt>Relevé</dt><dd>{date(card.observedAt)}</dd></div>
          <div><dt>Langue</dt><dd>{card.languageVerified ? "Vérifiée" : "Non vérifiée"}</dd></div>
          <div><dt>Disponibilité</dt><dd>{card.availability === "UNKNOWN" ? "Inconnue" : card.availability}</dd></div>
        </dl>
        <p>Prix indicatifs, pas des ventes conclues. La variante, la langue et l'état peuvent changer la valeur.</p>
      </details>
    </div>
  </article>;
}
export async function MarketDashboard() {
  const snapshot = await getTcgMarketSnapshot();
  const freshDate = snapshot.observedAt ? date(snapshot.observedAt) : "Non disponible";
  return <div className="native-dashboard edge-investor-home">
    <section className="edge-home-heading">
      <div><p className="native-eyebrow">EDGE · DÉCOUVERTE</p><h1>Le marché, sous un autre angle<span>.</span></h1><p>Explore les produits et repère les pistes à investiguer.</p></div>
      <Link href="/mri" className="edge-home-action">Voir les analyses <span aria-hidden="true">↗</span></Link>
    </section>
    <section className="edge-home-market" aria-labelledby="edge-market-title">
      <div className="edge-home-section-head"><div><p className="native-eyebrow">01 / EXPLORER</p><h2 id="edge-market-title">Produits observés <span>{snapshot.cards.length}</span></h2></div><div className="edge-home-section-actions"><span className="edge-home-updated">Relevé : {freshDate}</span><Link href="/explorer" className="edge-explore-link">Tout explorer →</Link></div></div>
      {snapshot.cards.length ? <div className="edge-asset-grid">{snapshot.cards.map(card => <CardTile key={card.productId} card={card}/>)}</div> : <div className="edge-home-empty"><strong>Aucun produit disponible actuellement</strong><p>Les produits apparaîtront ici lorsqu'un relevé vérifiable sera accessible. Aucun prix n'est simulé.</p></div>}
      {snapshot.warning && <details className="edge-home-data-note"><summary>État des données</summary><p>{snapshot.warning}</p></details>}
    </section>
    <section className="edge-home-ai" aria-label="Intelligence EDGE">
      <div className="edge-home-ai-symbol" aria-hidden="true">✳</div>
      <div><p className="native-eyebrow">02 / EDGE INTELLIGENCE</p><h2>Au-delà du prix.</h2><p>Les enquêtes relient les observations aux événements du marché, aux risques et aux hypothèses d'investissement.</p><span className="edge-ai-state">Analyses à consulter · Agent conversationnel non activé</span></div>
      <Link href="/mri" className="edge-ai-link">Explorer les analyses <span aria-hidden="true">→</span></Link>
    </section>
    <details className="edge-home-help">
      <summary>Comprendre les données et les limites d'EDGE <span aria-hidden="true">＋</span></summary>
      <div><p>Les prix affichés sont indicatifs : une annonce ou un agrégat n'est pas une vente conclue. Les variantes, langues et états doivent être vérifiés avant toute décision.</p><p>Une investigation est une hypothèse à examiner, jamais une garantie de rendement ni une autorisation d'achat. Les détails des sources figurent dans chaque carte.</p><p>État du relevé : {snapshot.status}. Relevés exploitables : {snapshot.successfulCount}. Relevés incomplets : {snapshot.failedCount}. Ventes conclues identifiées : {snapshot.completedSales}.</p></div>
    </details>
  </div>;
}
