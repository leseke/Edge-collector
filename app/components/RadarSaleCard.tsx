import { RadarProductZoom } from "./RadarProductZoom";
import { AssetImage } from "./AssetImage";
import type { RadarSale } from "../lib/radar-paid-sales";

const catalogueArt = {
  "swsh7-215": { series: "Évolution Céleste", language: "fr", image: "https://assets.tcgdex.net/fr/swsh/swsh7/215/high.webp" },
  "swsh8-157": { series: "Poing de Fusion", language: "en", image: "https://assets.tcgdex.net/en/swsh/swsh8/157/high.png" },
};

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function RadarSaleCard({ sale }: { sale: RadarSale }) {
  const id = sale.key.split(":")[0];
  const art = catalogueArt[id as keyof typeof catalogueArt];
  const host = new URL(sale.source).hostname;
  const platform = host === "gradedcardcenter.com" ? "Graded Card Center" : host;
  const variant = sale.variant.replace(/\bFR\b/, "Français").replace(/\bIT\b/, "Italien")
    .replace(/\bEN\b/, "Anglais");
  return <RadarProductZoom name={sale.name}>
    <div className="radar-sale-art">
      <AssetImage src={art?.image ?? null} name={sale.name + (art?.language === "en" ? " (édition anglaise)" : "")} />
      {art && <small>{art.language === "en" ? "Visuel catalogue EN" : "Visuel catalogue FR"}</small>}
    </div>
    <div className="radar-sale-main">
      <h3>{sale.name}</h3>
      {art && <p className="radar-sale-series">{art.series}</p>}
      <p className="radar-sale-variant">{variant}</p>
      <div className="radar-sale-price"><strong>{euros.format(sale.cents / 100)}</strong><span>payé le <time dateTime={sale.day}>{date.format(new Date(sale.day))}</time></span></div>
      <a className="radar-sale-source" href={sale.source} target="_blank" rel="noopener noreferrer"
        aria-label={`Voir la vente de ${sale.name} sur ${platform}`}>
        {platform} <span aria-hidden="true">↗</span>
      </a>
    </div>
  </RadarProductZoom>;
}
