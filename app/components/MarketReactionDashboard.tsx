import { Suspense } from "react";
import Link from "next/link";
import { getTcgMarketSnapshot } from "../lib/market-data";
import { getRadarPaidSales } from "../lib/radar-paid-sales";
import { LeboncoinWatchPanel } from "./LeboncoinWatchPanel";
import { CardLiquidityPanel } from "./CardLiquidityPanel";
import { RadarSaleCard } from "./RadarSaleCard";
import { GccAvailability } from "./GccAvailability";

const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });
const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const signed = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

function PaidSalesList({ sales }: { sales: Awaited<ReturnType<typeof getRadarPaidSales>>["recentSales"] }) {
  return <ul className="radar-sales">
    {sales.map(sale => <li key={sale.id}><RadarSaleCard sale={sale} /></li>)}
  </ul>;
}

export async function MarketReactionDashboard() {
  const [snapshot, sales] = await Promise.all([getTcgMarketSnapshot(), getRadarPaidSales()]);
  const pokemonCases = snapshot.reactionCases.filter(item => item.productId.startsWith("pokemon_card_"));
  const guides = snapshot.cards.filter(card => card.guideWindow);
  return <div className="native-dashboard radar-dashboard">
    <header className="radar-intro">
      <h1>Radar Pokémon</h1>
      <p>Consulte les ventes de cartes, boosters et coffrets Pokémon. Pour évaluer une annonce, compare-la aux ventes de la même version, dans la même langue et au même grade.</p>
      <div className="radar-actions">
        <a className="radar-action primary" href="#analyse-annonce">Analyser une annonce</a>
        <a className="radar-action" href="#ventes-payees">Voir les ventes payées</a>
        <a className="radar-action" href="#disponibilite">Voir les offres ouvertes</a>
      </div>
    </header>

    <section id="ventes-payees" className="dashboard-section radar-section" aria-labelledby="radar-sales-title">
      <h2 id="radar-sales-title">{sales.archiveOnly ? "Ventes payées archivées" : "Dernières ventes payées"}</h2>
      <p className="radar-sales-description">{sales.archiveOnly ?
        "Les ventes déjà documentées restent consultables pendant l’indisponibilité de la collecte." :
        "Transactions payées que EDGE a pu vérifier. La liste couvre une partie des ventes de Graded Card Center."}</p>
      {sales.recentSales.length ? <PaidSalesList sales={sales.recentSales} /> : <p>Aucune vente payée documentée pour le moment.</p>}
      {sales.otherSales.length > 0 && <details className="radar-disclosure">
        <summary>Autres ventes relevées ({sales.otherSales.length})</summary>
        <PaidSalesList sales={sales.otherSales} />
      </details>}
    </section>

    <section id="disponibilite" className="dashboard-section radar-section" aria-labelledby="radar-availability-title">
      <h2 id="radar-availability-title">Disponibilité</h2>
      <p className="radar-sales-description">Aperçu des annonces Pokémon ouvertes sur Graded Card Center, jusqu’à huit par type. Les prix affichés peuvent évoluer.</p>
      <Suspense fallback={<p>Chargement des enchères en cours…</p>}><GccAvailability kind="auction" /></Suspense>
      <Suspense fallback={<p>Chargement des offres à prix fixe…</p>}><GccAvailability kind="fixed" /></Suspense>
      <details className="radar-disclosure">
        <summary>Fréquence des ventes par variante</summary>
        <CardLiquidityPanel cards={sales.cards} scan={sales.scan} />
      </details>
    </section>

    <LeboncoinWatchPanel cards={sales.variants} />

    <section className="dashboard-section radar-section" aria-labelledby="radar-trends-title">
      <h2 id="radar-trends-title">Tendances du marché</h2>
      {sales.trends.length === 0 && <p>Pas assez de ventes payées comparables pour mesurer une tendance sur 30 jours.</p>}
      {sales.trends.slice(0, 12).map(trend => {
        const variant = sales.variants.find(item => item.key === trend.key);
        if (!variant) return null;
        return <article className="edge-mri-case" key={trend.key}>
          <h3>{variant.name} · {variant.variant}</h3>
          <p>Prix médian {signed.format(trend.priceChange)} % · {trend.priorCount} puis {trend.recentCount} ventes sur deux périodes de 30 jours.</p>
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
    </section>
  </div>;
}
