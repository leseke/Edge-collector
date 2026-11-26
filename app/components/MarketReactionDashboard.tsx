import { CatalystPanel } from "./CatalystPanel";
import { MarketPatternPanel } from "./MarketPatternPanel";
import { LearningPanel } from "./LearningPanel";
import { ResearchAlertInbox } from "./ResearchAlertInbox";
import { OfferPriceSignals } from "./OfferPriceSignals";
import { OpportunityScanner } from "./OpportunityScanner";
import { Suspense } from "react";
import Link from "next/link";
import { getTcgMarketSnapshot } from "../lib/market-data";
import { getRadarPaidSales } from "../lib/radar-paid-sales";
import { LeboncoinWatchPanel } from "./LeboncoinWatchPanel";
import { CardLiquidityPanel } from "./CardLiquidityPanel";
import { RadarSaleCard } from "./RadarSaleCard";
import { GccAvailability } from "./GccAvailability";
import { gccCursor, gccSeries } from "../lib/gcc-active-listings";

const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });
const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const signed = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

const radarTabs = [
  { id: "signaux", title: "Signaux" },
  { id: "offres", title: "Offres" },
  { id: "ventes", title: "Ventes" },
  { id: "marche", title: "Marché" },
] as const;

function PaidSalesList({ sales }: { sales: Awaited<ReturnType<typeof getRadarPaidSales>>["recentSales"] }) {
  return <ul className="radar-sales">
    {sales.map(sale => <li key={sale.id}><RadarSaleCard sale={sale} /></li>)}
  </ul>;
}

export async function MarketReactionDashboard({ params = {} }: { params?: Record<string, unknown> }) {
  const tab = radarTabs.find(item => item.id === params.tab)?.id ?? (params.closed || params.serie ? "ventes" : params.auction || params.fixed ? "offres" : "signaux");
  const [snapshot, sales] = await Promise.all([getTcgMarketSnapshot(), getRadarPaidSales()]);
  const pokemonCases = snapshot.reactionCases.filter(item => item.productId.startsWith("pokemon_card_"));
  const guides = snapshot.cards.filter(card => card.guideWindow);
  return <div className="native-dashboard radar-dashboard edge-radar-premium">
    <header className="radar-intro">
      <p className="native-eyebrow">MARKET INTELLIGENCE</p><h1>Radar Pokémon<span>.</span></h1>
      <p>Opportunités, transactions et mouvements du marché.</p>
      <nav aria-label="Rubriques du Radar" className="edge-radar-tabs">
        {radarTabs.map(item => <Link key={item.id} href={`/mri?tab=${item.id}`} aria-current={tab === item.id ? "page" : undefined} className="edge-radar-tab">{item.title}</Link>)}
      </nav>
    </header>

    {tab === "ventes" && <>
    <section id="ventes-payees" className="dashboard-section radar-section" aria-labelledby="radar-sales-title">
      <h2 id="radar-sales-title" className="radar-section-title" data-tone="mint">{sales.archiveOnly ? "Ventes payées archivées" : "Dernières ventes payées"}</h2>
      <p className="radar-sales-description">{sales.archiveOnly ?
        "Les ventes déjà documentées restent consultables pendant l’indisponibilité de la collecte." :
        "Transactions payées que EDGE a pu vérifier. La liste couvre une partie des ventes de Graded Card Center."}</p>
      {sales.recentSales.length ? <PaidSalesList sales={sales.recentSales} /> : <p>Aucune vente payée documentée pour le moment.</p>}
      {sales.otherSales.length > 0 && <details className="radar-disclosure">
        <summary>Autres ventes relevées ({sales.otherSales.length})</summary>
        <PaidSalesList sales={sales.otherSales} />
      </details>}
    </section>

    <section id="gcc-closed" className="dashboard-section radar-section" aria-labelledby="radar-history-title">
      <h2 id="radar-history-title" className="radar-section-title" data-tone="lilac">Ventes clôturées sur GCC</h2>
      <Suspense fallback={<p>Chargement de l’historique GCC…</p>}>
        <GccAvailability variants={sales.variants} kind="closed" cursor={gccCursor(params.closed)} series={gccSeries(params.serie)} />
      </Suspense>
    </section>

    </>}
    {tab === "offres" && <>
    <section id="disponibilite" className="dashboard-section radar-section" aria-labelledby="radar-availability-title">
      <h2 id="radar-availability-title" className="radar-section-title" data-tone="blue">Offres ouvertes</h2>
      <p className="radar-sales-description">Parcours les annonces Pokémon ouvertes sur Graded Card Center. Les prix sont ceux du relevé et peuvent évoluer.</p>
      <nav className="radar-offer-links" aria-label="Types d’offres ouvertes">
        <a href="#gcc-auction">Enchères en cours <span aria-hidden="true">↓</span></a>
        <a href="#gcc-fixed">Offres à prix fixe <span aria-hidden="true">↓</span></a>
      </nav>
      <div id="gcc-auction" className="radar-offer-list">
        <Suspense fallback={<p>Chargement des enchères en cours…</p>}><GccAvailability variants={sales.variants} kind="auction" cursor={gccCursor(params.auction)} /></Suspense>
      </div>
      <div id="gcc-fixed" className="radar-offer-list">
        <Suspense fallback={<p>Chargement des offres à prix fixe…</p>}><GccAvailability variants={sales.variants} kind="fixed" cursor={gccCursor(params.fixed)} /></Suspense>
      </div>
      <details className="radar-disclosure">
        <summary>Fréquence des ventes par variante</summary>
        <CardLiquidityPanel cards={sales.cards} scan={sales.scan} />
      </details>
    </section>

    <LeboncoinWatchPanel cards={sales.variants} />
    </>}

    {tab === "signaux" && <div className="edge-signal-workspace">
      <section className="edge-signal-overview" aria-label="Synthèse des signaux">
        <div className="edge-signal-heading"><div><p className="native-eyebrow">RADAR · RECHERCHE</p><h2>Centre de décision</h2></div><Link href="/follow">Suivi ↗</Link></div>
        <div className="edge-signal-stats">
          <div><strong>{snapshot.status==="UNAVAILABLE"?"—":pokemonCases.filter(p=>p.publications.length>0).length}</strong><span>Produits Pokémon cités</span></div>
          <div><strong>{sales.archiveOnly?"—":sales.leads.length}</strong><span>Sources à vérifier</span></div>
          <div><strong>{sales.archiveOnly?"—":sales.trends.length}</strong><span>Tendances mesurées</span></div>
        </div>
        <p>Indices de recherche, distincts des opportunités d’achat. {sales.archiveOnly?"Ventes archivées uniquement.":"Échantillons documentés, couverture non exhaustive."}</p>
      </section>
      <nav className="edge-signal-nav" aria-label="Analyses des signaux">
        {[["opportunites","Opportunités","edge-radar-opportunities"],["alertes","Alertes","edge-radar-notifications"],["catalyseurs","Catalyseurs","edge-radar-catalysts"],["precurseurs","Précurseurs","edge-radar-patterns"],["prix","Prix","edge-radar-price"],["pistes","Pistes","edge-radar-early"]].map(([key,title,id])=><a key={key} href={"#"+id}>{title}</a>)}
      </nav>
      <div id="edge-radar-opportunities" className="edge-radar-module"><Suspense fallback={<p>Analyse des offres GCC en cours…</p>}><OpportunityScanner variants={sales.variants} archiveOnly={sales.archiveOnly} /></Suspense></div>
      <div id="edge-radar-notifications" className="edge-radar-module"><Suspense fallback={<p>Chargement des notifications…</p>}><ResearchAlertInbox params={params} /></Suspense></div>
      <details id="edge-radar-catalysts" className="edge-signal-fold" open={params.alert===undefined && params.signal==="catalyseurs"?true:undefined}><summary><span><strong>Catalyseurs</strong><small>Publications, événements et comparaisons</small></span></summary><Suspense fallback={<p>Recherche des catalyseurs…</p>}><CatalystPanel snapshot={snapshot} /></Suspense></details>
      <details id="edge-radar-patterns" className="edge-signal-fold"><summary><span><strong>Précurseurs</strong><small>Volume, offre et absorption</small></span></summary><Suspense fallback={<p>Recherche des configurations…</p>}><MarketPatternPanel variants={sales.variants} /></Suspense></details>
      <details id="edge-radar-price" className="edge-signal-fold"><summary><span><strong>Mouvements de prix</strong><small>Variations observées</small></span></summary><Suspense fallback={<p>Recherche des variations de prix…</p>}><OfferPriceSignals variants={sales.variants} /></Suspense></details>
    </div>}
    
    {tab === "marche" && <Suspense fallback={<p>Évaluation des signaux…</p>}><LearningPanel horizonValue={params.horizon} /></Suspense>}

    {(tab === "signaux" || tab === "marche") && <section id={tab==="signaux"?"edge-radar-early":undefined} className="dashboard-section radar-section" aria-labelledby="radar-trends-title">
      <h2 id="radar-trends-title">{tab === "signaux" ? "Signaux à investiguer" : "Tendances du marché"}</h2>
      {tab === "signaux" && <p>Les tendances observées sont des pistes de recherche, pas des recommandations d’achat.</p>}
      {tab === "signaux" && <section aria-label="Signaux précoces">
        <h3>Pistes avant confirmation du marché</h3>
        <p>Une publication peut déclencher une investigation sans historique de ventes suffisant. Son impact commercial reste à vérifier.</p>
        {pokemonCases.filter(item => item.publications.length > 0).map(item => <article className="edge-mri-case" key={item.productId}>
          <small>SIGNAL FAIBLE · À INVESTIGUER</small>
          <h3>{snapshot.cards.find(card => card.productId === item.productId)?.name ?? item.productId}</h3>
          <ul>{item.publications.map(publication => <li key={publication.url}><a href={publication.url} target="_blank" rel="noopener noreferrer">{publication.title}</a></li>)}</ul>
          <p>Hypothèse à tester : évolution de la demande, de la disponibilité ou des prix après publication. Aucun rendement présumé.</p>
          <Link href={`/explorer/${encodeURIComponent(item.productId)}`}>Examiner le produit →</Link>
        </article>)}
        {!pokemonCases.some(item => item.publications.length > 0) && <p>Aucune publication liée à un produit dans le relevé actuel.</p>}
      </section>}
      {sales.trends.length === 0 && <p>Pas assez de ventes payées comparables pour mesurer une tendance sur 30 jours.</p>}
      {sales.trends.slice(0, 12).map(trend => {
        const variant = sales.variants.find(item => item.key === trend.key);
        if (!variant) return null;
        return <article className="edge-mri-case" key={trend.key}>
          <h3>{variant.name} · {variant.variant}</h3>
          <div className="edge-trend-metric"><strong data-direction={trend.priceChange>0?"up":trend.priceChange<0?"down":"flat"}>{signed.format(trend.priceChange)} %</strong><span>Variation de la médiane</span></div><p>{trend.priorCount} puis {trend.recentCount} ventes sur deux périodes de 30 jours.</p>
          {trend.scenario !== "INDETERMINE" && <p>Scénario {trend.scenario.toLowerCase()} si le mouvement se poursuit.</p>}
          {trend.analogues > 0 && <p>Le mouvement s’est poursuivi dans {trend.continued} cas similaires sur {trend.analogues} observés pour cette variante.</p>}
        </article>;
      })}
      {sales.leads.length > 0 && <details className="radar-disclosure">
        <summary>Annonces et publications à vérifier</summary>
        <ul>{sales.leads.map(lead => <li key={lead.source_url}>
          <a href={lead.source_url} target="_blank" rel="noopener noreferrer">{new URL(lead.source_url).hostname} ↗</a>
          {" · "}{lead.category.toLowerCase()}{" · "}{lead.first_seen_day}
        </li>)}</ul>
      </details>}
      {tab === "marche" && <>
      <CardLiquidityPanel cards={sales.cards} scan={sales.scan} />
      <details className="radar-disclosure">
        <summary>Événements et sources Pokémon</summary>
        {pokemonCases.length === 0 && <p>Aucun événement Pokémon relié à un mouvement de marché dans le dernier relevé.</p>}
        {pokemonCases.map(item => {
          const card = snapshot.cards.find(entry => entry.productId === item.productId);
          return <article className="edge-mri-case" key={item.productId}>
            <h3>{card?.name ?? "Publication liée à une carte Pokémon"}</h3>
            <ul>{item.publications.map(publication => <li key={publication.url}>
              <a href={publication.url} target="_blank" rel="noopener noreferrer">{publication.title} ↗</a>
            </li>)}</ul>
            {card && <Link href={`/explorer/${encodeURIComponent(item.productId)}`}>Voir la fiche carte</Link>}
          </article>;
        })}
      </details>
      <details className="radar-disclosure">
        <summary>Prix indicatifs Cardmarket</summary>
        <p>Moyennes via TCGdex sur 7 et 30 jours. Ces périodes se chevauchent et les prix regroupent des langues et des grades non précisés.</p>
        {guides.length === 0 && <p>Aucun repère de prix daté disponible.</p>}
        <ul>{guides.map(card => {
          const guide = card.guideWindow!;
          return <li key={card.productId}>
            <Link href={`/explorer/${encodeURIComponent(card.productId)}`}>{card.name} · {card.setName} · {card.number}</Link>
            {" · 7 j "}{euros.format(guide.avg7)}{" · 30 j "}{euros.format(guide.avg30)}
            <small> · {date.format(new Date(guide.updated))}{guide.stale ? " · relevé de plus de 48 h" : ""}</small>
          </li>;
        })}</ul>
      </details>
      <details className="radar-disclosure">
        <summary>Comment lire les tendances</summary>
        <p>EDGE compare les prix médians de deux périodes de 30 jours, avec au moins trois ventes par période pour la même variante. Les publications servent à dater un événement. Il faut ensuite des prix, des ventes ou des relevés d’offre comparables pour mesurer la réaction du marché.</p>
      </details>
      </>}
    </section>}
  </div>;
}
