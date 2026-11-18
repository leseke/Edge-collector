import { rankFixedOffers } from "../lib/fixed-offer-ranking";
import { scanFixedOffers } from "../lib/fixed-offer-pages";
import { getGccActiveListings } from "../lib/gcc-active-listings";
import { listingCardKey } from "../lib/comparable-sales";
import type { SaleVariant } from "../lib/radar-paid-sales";
import { GccProductImage, RadarProductZoom, ZoomComparables } from "./RadarProductZoom";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const price = (cents: number) => euros.format(cents / 100);
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeZone: "UTC" });
const checked = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });
const groups = [
  { reason: "gap", label: "Sous la médiane", tone: "mint" },
  { reason: "series", label: "Séries à surveiller", tone: "lilac" },
  { reason: "single", label: "Vente de référence isolée", tone: "blue" },
];

function OfferCards({ rows }: { rows: ReturnType<typeof rankFixedOffers> }) {
  return <ul className="radar-sales">{rows.map(row => <li key={row.item.id}>
    <RadarProductZoom name={row.item.title}>
      <div className="radar-sale-art">{row.item.image && <GccProductImage src={row.item.image} name={row.item.title} />}</div>
      <div className="radar-sale-main">
        <h4 className="radar-gcc-lot-title">{row.item.title}</h4>
        <p className="radar-sale-variant">{row.item.variant}</p>
        <div className="radar-sale-price"><strong>{price(row.cost)}</strong><span>livré estimé</span></div>
        {row.median !== null && <p className="rank-evidence">{price(row.gap!)} sous la médiane de {price(row.median)} hors livraison.</p>}
        {row.reason === "series" && <p className="rank-evidence">{row.recent} ventes de la série sur 7 jours, contre {row.previous} les 7 jours précédents. Demande pour cette variante à confirmer.</p>}
        <small>{row.last ? <>{row.count} vente{row.count > 1 ? "s" : ""} comparable{row.count > 1 ? "s" : ""} · Dernière à {price(row.last.cents)} le {date.format(new Date(row.last.day))}</> : "Aucune vente comparable documentée."}</small>
        <ZoomComparables cardKey={listingCardKey(row.item.title, row.item.variant, row.item.series)} lotId={"gcc-" + row.item.id} basis={{ kind: "fixed", cents: row.item.cents }} />
        <a className="radar-sale-source" href={"https://gradedcardcenter.com/item/" + row.item.id} target="_blank" rel="noopener noreferrer">Voir le lot sur GCC ↗</a>
      </div>
    </RadarProductZoom>
  </li>)}</ul>;
}

export async function FixedOfferRanking({ variants }: { variants: SaleVariant[] }) {
  const scan = await scanFixedOffers(cursor => getGccActiveListings("fixed", cursor));
  if (!scan.pages) return <p role="status">Catalogue GCC momentanément indisponible. Aucune page analysée.</p>;
  const ranked = rankFixedOffers(scan.items, variants, new Date().toISOString().slice(0, 10));
  return <>
    <p className="rank-coverage">{scan.items.length} offres distinctes · {scan.pages} page{scan.pages > 1 ? "s" : ""} GCC · {scan.status === "end" ? "Dernière page atteinte" : scan.status === "partial" ? "Lecture interrompue" : "Couverture partielle"}
      <small>Relevé le plus ancien · {checked.format(new Date(scan.oldest))} (Paris)</small></p>
    {!ranked.length && <p>Aucune offre ne ressort des pages analysées avec les ventes actuellement documentées.</p>}
    {groups.map(group => {
      const rows = ranked.filter(row => row.reason === group.reason);
      if (!rows.length) return null;
      return <section className="rank-group" key={group.reason} data-tone={group.tone}>
        <h3>{group.label} <span>({rows.length})</span></h3>
        <OfferCards rows={rows.slice(0, 3)} />
        {rows.length > 3 && <details className="radar-disclosure"><summary>Voir les {rows.length - 3} autres offres</summary><OfferCards rows={rows.slice(3)} /></details>}
      </section>;
    })}
    <a className="radar-sale-source" href="#gcc-fixed">Parcourir le catalogue à prix fixe ↓</a>
  </>;
}
