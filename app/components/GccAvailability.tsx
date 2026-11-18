import { gccListingPages, getGccActiveListings } from "../lib/gcc-active-listings";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });

export async function GccAvailability({ kind }: { kind: "auction" | "fixed" }) {
  const auction = kind === "auction";
  const data = await getGccActiveListings(kind);
  return <div className="radar-active-group">
    <h3>{auction ? "Enchères en cours" : "Offres à prix fixe"}</h3>
    {data ? <p className="radar-sales-description">Relevé du {date.format(new Date(data.checkedAt))} · Graded Card Center</p> :
      <p className="radar-sales-description">Le relevé est momentanément indisponible.</p>}
    {data && !data.items.length && <p>Aucune annonce Pokémon confirmée sur cette page au moment du relevé.</p>}
    {!!data?.items.length && <ul className="radar-sales">
      {data.items.map(item => <li key={item.id}>
        <article className="radar-sale-card">
          <div className="radar-sale-art">
            {item.image ? <img src={item.image} alt={item.title} loading="lazy" /> : <small>Photo sur GCC</small>}
          </div>
          <div className="radar-sale-main">
            <h4>{item.title}</h4>
            <p className="radar-sale-variant">{item.variant}</p>
            <div className="radar-sale-price"><strong>{euros.format(item.cents / 100)}</strong>
              <span>{auction ? "Enchère affichée" : "Prix demandé"}</span>
            </div>
            {item.ends && <p className="radar-sale-variant">Fin le {item.ends.replace(" @ ", " à ")}</p>}
            <a className="radar-sale-source" href={`https://gradedcardcenter.com/item/${item.id}`} target="_blank" rel="noopener noreferrer">
              Voir sur Graded Card Center ↗
            </a>
          </div>
        </article>
      </li>)}
    </ul>}
    <a className="radar-sale-source" href={gccListingPages[kind]} target="_blank" rel="noopener noreferrer">
      {auction ? "Toutes les enchères Pokémon sur GCC" : "Toutes les offres Pokémon à prix fixe sur GCC"} ↗
    </a>
  </div>;
}
