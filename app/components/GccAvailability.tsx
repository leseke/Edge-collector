import { GccCoverage } from "./GccCoverage";
import type { SaleVariant } from "../lib/radar-paid-sales";
import { GccProductImage, RadarProductZoom } from "./RadarProductZoom";
import { Suspense } from "react";
import { gccListingPages, getGccActiveListings, getGccSeries, type GccListingKind } from "../lib/gcc-active-listings";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });
const integer = new Intl.NumberFormat("fr-FR");
const titles = { auction: "Enchères en cours", fixed: "Offres à prix fixe", closed: "Ventes clôturées sur GCC" };

function gccRadarUrl(kind: GccListingKind, cursor: string | null, series?: string | null) {
  const params = new URLSearchParams();
  if (cursor) params.set(kind, cursor);
  if (series) params.set("serie", series);
  const query = params.toString();
  return "/mri" + (query ? "?" + query : "") + "#gcc-" + kind;
}

async function GccSeriesChoices({ choices }: { choices: Promise<string[]> }) {
  return <datalist id="gcc-series">{(await choices).map(choice => <option key={choice} value={choice} />)}</datalist>;
}

export async function GccAvailability({ kind, variants, cursor = null, series = null }: {
  variants: SaleVariant[]; kind: GccListingKind; cursor?: string | null; series?: string | null;
}) {
  const auction = kind === "auction";
  const closed = kind === "closed";

  const choices = closed ? getGccSeries() : null;
  const data = await getGccActiveListings(kind, cursor, series);
  const grouped = new Map<string, NonNullable<typeof data>["items"]>();
  for (const item of data?.items ?? []) {
    const label = closed ? item.series ?? "Série non renseignée" : "";
    const group = grouped.get(label);
    if (group) group.push(item);
    else grouped.set(label, [item]);
  }
  const byKey = new Map(variants.map(variant => [variant.key, variant.paidSales]));
  const groups = [...grouped].sort(([left], [right]) => left.localeCompare(right, "fr"));
  return <div className="radar-active-group">
    {!closed && <h3>{titles[kind]}</h3>}
    <Suspense fallback={null}><GccCoverage kind={kind} /></Suspense>
    {closed && <div>
      <p className="radar-sales-description">Historique public de GCC. Les lots en attente de paiement sont signalés.</p>
      <form action="/mri#gcc-closed" className="radar-listing-form">
        <label htmlFor="gcc-set">Filtrer les ventes par série Pokémon</label>
        <input id="gcc-set" name="serie" list="gcc-series" defaultValue={series ?? ""} maxLength={100} placeholder="Ex. Héros Transcendants" />
        <button type="submit">Filtrer</button>
      </form>
      {choices && <Suspense fallback={null}><GccSeriesChoices choices={choices} /></Suspense>}
      {series && <a className="radar-sale-source" href={gccRadarUrl(kind, null)}>Toutes les séries ↗</a>}
    </div>}
    {data ? <p className="radar-sales-description">
      Page {data.page}{data.total !== null && <> · {integer.format(data.total)} résultats signalés par GCC</>}
      {" · Relevé du "}{date.format(new Date(data.checkedAt))}
    </p> : <p className="radar-sales-description">La page GCC est momentanément indisponible.</p>}
    {data && !data.items.length && <p>Aucun lot Pokémon à afficher sur cette page.</p>}
    {groups.map(([label, items]) => <div className="radar-gcc-series" key={label}>
      {closed && <h3 className="radar-series-heading">{!series && items[0].series ? <a href={gccRadarUrl(kind, null, label)}>{label}</a> : label}</h3>}
      <ul className="radar-sales">
        {items.map(item => {
          const matches = ((item.variantKey && byKey.get(item.variantKey)) || [])
            .filter(sale => sale.source !== `https://gradedcardcenter.com/item/${item.id}`)
            .sort((a, b) => b.day.localeCompare(a.day));
          return <li key={item.id}>
          <RadarProductZoom name={item.title} details={<section aria-label="Ventes comparables">
            <h3>Ventes payées comparables</h3>
            {matches.length ? <>
              <p>{matches.length} {matches.length === 1 ? "vente comparable" : "ventes comparables"} dans l’historique EDGE.</p>
              <ul>{matches.slice(0, 5).map(sale => <li key={sale.id}>
                <a href={sale.source} target="_blank" rel="noopener noreferrer">{euros.format(sale.cents / 100)} · {new Date(sale.day).toLocaleDateString("fr-FR", { timeZone: "UTC" })} · Payé sur GCC ↗</a>
              </li>)}</ul>
            </> : <p>{item.variantKey ? "Aucune vente payée comparable dans l’historique consulté." : "Les caractéristiques de ce lot ne permettent pas une comparaison exacte."}</p>}
          </section>}>
            <div className="radar-sale-art">
              {item.image ? <GccProductImage src={item.image} name={item.title} /> : <small>Photo sur GCC</small>}
            </div>
            <div className="radar-sale-main">
              <h4 className="radar-gcc-lot-title">{item.title}</h4>
              <p className="radar-sale-variant">{item.variant}</p>
              <div className="radar-sale-price">
                <strong>{item.cents === null ? "Prix indisponible" : euros.format(item.cents / 100)}</strong>
                <span>{auction ? "Enchère affichée" : closed ? "Prix indiqué par GCC" : "Prix demandé"}</span>
              </div>
              {item.ends && <p className="radar-sale-variant">Fin le {date.format(new Date(item.ends))}</p>}
              {closed && <p className="radar-sale-variant">{item.awaitingPayment ? "En attente de paiement" : "Vendu selon GCC"}
                {item.soldAt && <> · {date.format(new Date(item.soldAt))}</>}
              </p>}
              <a className="radar-sale-source" href={`https://gradedcardcenter.com/item/${item.id}`} target="_blank" rel="noopener noreferrer">Voir sur Graded Card Center ↗</a>
            </div>
          </RadarProductZoom>
        </li>;
        })}
      </ul>
    </div>)}
    <nav className="radar-actions" aria-label={`Pagination de la rubrique ${titles[kind]}`}>
      {cursor && <a className="radar-action" href={gccRadarUrl(kind, null, series)}>Première page</a>}
      {data?.nextCursor && data.nextCursor !== cursor &&
        <a className="radar-action primary" href={gccRadarUrl(kind, data.nextCursor, series)}>Page suivante</a>}
      <a className="radar-sale-source" href={gccListingPages[kind]} target="_blank" rel="noopener noreferrer">Ouvrir la liste sur GCC ↗</a>
    </nav>
  </div>;
}
