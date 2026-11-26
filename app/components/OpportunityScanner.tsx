import { getMemoryOpportunities } from "../lib/memory-opportunities";
import { getGccActiveListings } from "../lib/gcc-active-listings";
import { rankFixedOffers, resaleFeePercent } from "../lib/listing-analysis";
import type { SaleVariant } from "../lib/radar-paid-sales";
import { GccProductImage, RadarProductZoom } from "./RadarProductZoom";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const money = (cents: number) => euros.format(cents / 100);
const day = new Intl.DateTimeFormat("fr-FR", {dateStyle:"medium",timeZone:"UTC"});
const maxPages = 3;

export async function OpportunityScanner({ variants, archiveOnly }: { variants: SaleVariant[]; archiveOnly: boolean }) {
  const memory=await getMemoryOpportunities();
  if(memory&&memory.latest)return <section className="dashboard-section radar-section" aria-labelledby="opportunity-title">
    <h2 id="opportunity-title">Scanner d’opportunités</h2>
    <p>Prospection autonome · évaluations enregistrées au cours des 48 dernières heures.</p>
    <div className="edge-scan-metrics"><div><span>Lots évalués</span><strong>{memory.examined}</strong></div><div><span>Pistes récentes</span><strong>{memory.candidates}</strong></div><div><span>Marge théorique positive</span><strong>{memory.positive}</strong></div></div>
    <p className="radar-sales-description">Dernière évaluation : {new Date(memory.latest).toLocaleString("fr-FR",{timeZone:"Europe/Paris"})}. Disponibilité à revérifier.</p>
    {memory.items.length===0?<p>Aucune piste répondant aux critères dans la mémoire récente. Les lots sans comparables restent non évaluables par cette méthode.</p>:<ul className="radar-sales edge-opportunity-list">{memory.items.map(item=>{
      const image=item.image_url&&/^https:\/\/cdn\.gradedcardcenter\.com\/image\/width=300,fit=contain,format=webp,quality=65\/item\/[A-Za-z0-9_-]{1,120}$/.test(item.image_url)?item.image_url:null;
      return <li key={item.lot_id}><RadarProductZoom name={item.title}>
        <div className="radar-sale-art">{image?<GccProductImage src={image} name={item.title}/>:<small>Photo sur GCC</small>}</div>
        <div className="radar-sale-main"><h3>{item.title}</h3><p className="radar-sale-variant">Évaluée le {day.format(new Date(item.observed_at))}</p>
          <div className="radar-sale-price"><strong>{money(item.asking_cents)}</strong><span>Dernier prix demandé observé</span></div>
          <div className="radar-price-comparison"><strong className="edge-opportunity-gap">−{(100*(item.median_cents-item.asking_cents)/item.median_cents).toFixed(1)} % <small>sous la médiane</small></strong>
          <small>Médiane : {money(item.median_cents)} · {item.comparable_count} ventes / 90 j à la date de l’évaluation</small>
          <div className="edge-opportunity-margin" data-positive={item.headroom_cents>0}><span>Marge théorique avant frais d’achat</span><b>{money(item.headroom_cents)}</b><small>Frais de revente supposés : {item.resale_fee_percent} %</small></div></div>
          {/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(item.lot_id)&&<a className="radar-sale-source" href={"https://gradedcardcenter.com/item/"+item.lot_id} target="_blank" rel="noopener noreferrer">Vérifier sur GCC ↗</a>}
        </div></RadarProductZoom></li>;
    })}</ul>}
    <details className="radar-disclosure"><summary>Couverture et méthode</summary><p>Classement des 12 premières pistes parmi les dernières évaluations de lots distincts. Les ventes payées documentées et annonces non retrouvées sont exclues. Une observation récente ne garantit pas la disponibilité. Aucun filtre de capital. Le nombre de lots évalués ne représente pas l’intégralité du marché.</p></details>
    <a className="radar-sale-source" href="/follow">Consulter les pistes mémorisées ↗</a>
  </section>;
  const offers = new Map<string, NonNullable<Awaited<ReturnType<typeof getGccActiveListings>>>["items"][number]>();
  const cursors = new Set<string>();
  let cursor: string | null = null, pages = 0, total: number | null = null, partial = false, checkedAt: string | null = null;
  for (let index = 0; index < maxPages; index++) {
    const page: Awaited<ReturnType<typeof getGccActiveListings>> = await getGccActiveListings("fixed", cursor);
    if (!page) { partial = true; break; }
    pages++;
    if (index === 0) total = page.total;
    checkedAt = [checkedAt ?? page.checkedAt, page.checkedAt].sort()[0];
    for (const offer of page.items) if (!offers.has(offer.id)) offers.set(offer.id, offer);
    if (!page.nextCursor) break;
    if (cursors.has(page.nextCursor)) { partial = true; break; }
    cursors.add(page.nextCursor);
    cursor = page.nextCursor;
    if (index === maxPages - 1) partial = true;
  }
  const ranked = rankFixedOffers([...offers.values()], variants, new Date().toISOString().slice(0,10));
  return <section className="dashboard-section radar-section" aria-labelledby="opportunity-title">
    <h2 id="opportunity-title">Scanner d’opportunités</h2>
    <p>Prix fixes GCC sous la médiane des ventes payées de la même variante. Aucun filtre de capital.</p>
    <div className="edge-scan-metrics"><div><span>Offres examinées</span><strong>{pages ? offers.size : "—"}</strong></div><div><span>Pistes détectées</span><strong>{pages ? ranked.length : "—"}</strong></div><div><span>Couverture</span><strong>{pages === 0 ? "Indisponible" : partial ? "Partielle" : "Parcourue"}</strong></div></div>
    <details className="radar-disclosure edge-scan-method"><summary>Couverture et fraîcheur du relevé</summary><p className="radar-sales-description">{pages} page(s) · {offers.size} offres distinctes examinées{total !== null ? " sur " + total + " signalées par GCC" : ""} · {partial ? "couverture partielle" : "pages parcourues"}{archiveOnly ? " · historique archivé" : ""}{checkedAt ? " · relevé " + new Date(checkedAt).toLocaleString("fr-FR",{timeZone:"Europe/Paris"}) : ""}</p></details>
    {pages === 0 ? <p>Source momentanément indisponible.</p> : ranked.length === 0 ? <p>Aucun écart positif documenté dans cet échantillon. Les offres sans comparables récents ne sont pas évaluables par ce scanner.</p> : <>
      <p>{ranked.length} piste(s) détectée(s) · affichage des 12 premières. Hypothèse de frais de revente : {resaleFeePercent} %. Frais d’achat et livraison inconnus.</p>
      <ul className="radar-sales edge-opportunity-list">{ranked.slice(0,12).map(result => {
        const {offer} = result;
        return <li key={offer.id}><RadarProductZoom name={offer.title} details={<section className="radar-price-comparison"><h3>Ventes payées utilisées</h3><ul>{result.evidence.slice(0,8).map(sale => <li key={sale.id}><a href={sale.source} target="_blank" rel="noopener noreferrer">{money(sale.cents)} · {day.format(new Date(sale.day))} ↗</a></li>)}</ul></section>}>
          <div className="radar-sale-art">{offer.image ? <GccProductImage src={offer.image} name={offer.title}/> : <small>Photo sur GCC</small>}</div>
          <div className="radar-sale-main"><h3>{offer.title}</h3><p className="radar-sale-variant">{offer.variant}</p>
            <div className="radar-sale-price"><strong>{money(offer.cents!)}</strong><span>Prix demandé</span></div>
            <div className="radar-price-comparison"><strong className="edge-opportunity-gap">−{result.gapPercent.toFixed(1)} % <small>sous la médiane</small></strong>
              <small>Médiane : {money(result.medianCents)} · {result.comparableCount} ventes / 90 j</small>
              <small>Plafond de rentabilité théorique avant frais d’achat : {money(result.ceilingBeforeAcquisitionFees)}</small>
              <div className="edge-opportunity-margin" data-positive={result.headroomCents > 0}><span>Marge théorique avant frais d’achat</span><b>{money(result.headroomCents)}</b><small>{result.headroomCents > 0 ? "À investiguer" : "Marge prudente non positive"}</small></div>
            </div><a className="radar-sale-source" href={"https://gradedcardcenter.com/item/" + offer.id} target="_blank" rel="noopener noreferrer">Vérifier sur GCC ↗</a>
          </div>
        </RadarProductZoom></li>;
      })}</ul></>}
    <p className="radar-sales-description">Le plafond utilise la plus basse vente récente, après frais de revente supposés. Ce n’est ni une prévision ni un ordre d’achat. Mémoire récente indisponible : mode de secours limité à trois pages par consultation.</p>
  </section>;
}
