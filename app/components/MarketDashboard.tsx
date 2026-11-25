import Link from "next/link";
import { getRadarPaidSales } from "../lib/radar-paid-sales";
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
 return <article className="edge-v3-asset">
   <Link href={"/explorer/"+encodeURIComponent(card.productId)} className="edge-v3-asset-link" aria-label={card.name+" · "+card.setName+" · Voir la fiche"}>
    <div className="edge-v3-asset-art"><AssetImage src={card.image} name={card.name}/><span className="edge-v3-price-overlay" title="Prix indicatif bas" aria-label={"Prix indicatif bas : "+money(card.low,card.currency)}>{money(card.low,card.currency)}</span></div>
    <h3>{card.name}</h3><p>{card.setName} · #{card.number}</p>
   </Link>
   <details className="edge-v3-asset-source"><summary>Prix & sources</summary><dl><dt>Prix indicatif bas</dt><dd>{money(card.low,card.currency)}</dd><dt>Moyenne indicative</dt><dd>{money(card.average,card.currency)}</dd><dt>Tendance indicative</dt><dd>{money(card.trend,card.currency)}</dd><dt>Source</dt><dd>{card.source}</dd><dt>Relevé</dt><dd>{date(card.observedAt)}</dd><dt>Langue</dt><dd>{card.languageVerified?"Vérifiée":"Non vérifiée"}</dd><dt>Disponibilité</dt><dd>{card.availability==="UNKNOWN"?"Inconnue":card.availability}</dd></dl><p>Variante et état à confirmer. Prix indicatifs, pas des ventes conclues.</p></details>
 </article>;
}
export async function MarketDashboard() {
  const [snapshot, sales] = await Promise.all([getTcgMarketSnapshot(), getRadarPaidSales().catch(() => null)]);
  const earlyCases = snapshot.reactionCases.filter(item => item.productId.startsWith("pokemon_card_") && item.publications.length > 0);
  const freshDate = snapshot.observedAt ? date(snapshot.observedAt) : "Non disponible";
  return <div className="native-dashboard edge-investor-home">
    <header className="edge-v3-home-header"><div><p className="native-eyebrow">ESPACE INVESTISSEUR</p><h1>Vue d’ensemble</h1><p>Le marché des collectibles, à portée de main.</p></div><Link href="/mri" className="edge-v3-quiet-link">Radar ↗</Link></header>
    <form action="/explorer" className="edge-v3-search" role="search"><svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input name="catalogue" type="search" aria-label="Rechercher une carte Pokémon" placeholder="Rechercher une carte Pokémon…" maxLength={60} required/><button type="submit" aria-label="Lancer la recherche">→</button></form>
    <section className="edge-v3-market-summary" aria-label="Synthèse du marché">
      <div className="edge-v3-summary-head"><div><p>Marché observé</p><strong>{snapshot.status==="UNAVAILABLE"?"—":snapshot.cards.length}</strong><small>Produits dans le relevé EDGE</small></div><Link href="/explorer" className="edge-v3-gold-action">Explorer ↗</Link></div>
      <div className="edge-v3-metrics">
        {[{label:"Ventes payées",value:sales?sales.recentSales.length+sales.otherSales.length:"—",href:"/mri?tab=ventes",note:sales?.archiveOnly?"Archive":"Échantillon"},{label:"Pistes de recherche",value:sales||snapshot.status!=="UNAVAILABLE"?(sales?.leads.length??0)+earlyCases.length:"—",href:"/mri?tab=signaux",note:"À approfondir"},{label:"Tendances",value:sales?.trends.length??"—",href:"/mri?tab=marche",note:"Variantes comparables"}].map(m=><Link key={m.label} href={m.href}><span>{m.label}</span><strong>{m.value}</strong><small>{m.note}</small></Link>)}
      </div>
      <p className="edge-v3-summary-date">Relevé : {freshDate} · Aucun montant de portefeuille simulé.</p>
    </section>
    <section className="edge-home-priorities" aria-label="Priorités de recherche">
      <div><p className="native-eyebrow">RADAR · PRIORITÉS</p><h2>À investiguer</h2>
      <p>{earlyCases.length || sales?.leads.length || sales?.trends.length ? "Des observations méritent une analyse complémentaire." : !sales && snapshot.status === "UNAVAILABLE" ? "Les données du Radar sont indisponibles." : "Aucune piste documentée dans ce relevé. Cela ne signifie pas que le marché ne présente aucune opportunité."}</p>
      <span className="edge-ai-state">Les pistes ne constituent pas des recommandations d’achat.</span></div>
      {earlyCases.length > 0 && <div className="edge-priority-grid">{earlyCases.slice(0, 4).map(item => {
        const card = snapshot.cards.find(entry => entry.productId === item.productId);
        const publication = item.publications[0];
        return <article className="edge-priority-card" key={item.productId}>
          <AssetImage src={card?.image ?? null} name={card?.name ?? "Carte Pokémon"} />
          <div><small>SIGNAL FAIBLE · IMPACT NON ÉTABLI</small><h3>{card?.name ?? "Publication liée à une carte Pokémon"}</h3>
          <p>{publication.title}</p><p>{date(publication.publishedAt)} · {item.publications.length} source(s) affichée(s)</p>
          <a href={publication.url} target="_blank" rel="noopener noreferrer">Source ↗</a> · <Link href={`/explorer/${encodeURIComponent(item.productId)}`}>Examiner</Link></div>
        </article>;
      })}</div>}
      <Link href="/mri?tab=signaux" className="edge-ai-link">Ouvrir les signaux →</Link>
    </section>
    <section className="edge-home-market" aria-labelledby="edge-market-title">
      <div className="edge-home-section-head"><div><p className="native-eyebrow">01 / EXPLORER</p><h2 id="edge-market-title">Produits observés <span>{snapshot.cards.length}</span></h2></div><div className="edge-home-section-actions"><span className="edge-home-updated">Relevé : {freshDate}</span><Link href="/explorer" className="edge-explore-link">Tout explorer →</Link></div></div>
      {snapshot.cards.length ? <div className="edge-home-gallery">{snapshot.cards.map(card => <CardTile key={card.productId} card={card}/>)}</div> : <div className="edge-home-empty"><strong>Aucun produit disponible actuellement</strong><p>Les produits apparaîtront ici lorsqu'un relevé vérifiable sera accessible. Aucun prix n'est simulé.</p></div>}
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
