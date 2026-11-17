"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import type { TcgCard } from "../lib/market-data";
import { AssetImage } from "../components/AssetImage";

export function ExplorerGrid({ cards, warning }: { cards: TcgCard[]; warning: string | null }) {
  const [query, setQuery] = useState("");
  const [series, setSeries] = useState("ALL");
  const seriesOptions = useMemo(() => [...new Set(cards.map(card => card.setName))].sort((a,b) => a.localeCompare(b, "fr")), [cards]);
  const visible = useMemo(() => cards.filter(card => (series === "ALL" || card.setName === series) && [card.name,card.setName,card.number].some(v => v.toLocaleLowerCase("fr").includes(query.trim().toLocaleLowerCase("fr")))), [cards,query,series]);
  return <div className="native-dashboard edge-explorer">
    <p className="native-eyebrow">EDGE / CATALOGUE OBSERVÉ</p>
    <h1>Explorer les collections<span>.</span></h1>
    <p className="edge-explorer-intro">Recherche dans les produits réellement présents dans les relevés EDGE. Ce catalogue est encore partiel.</p>
    <div className="edge-explorer-filters">
      <label><span>Rechercher</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Carte, numéro, série…" /></label>
      <label><span>Série</span><select value={series} onChange={event => setSeries(event.target.value)}><option value="ALL">Toutes les séries</option>{seriesOptions.map(name => <option key={name} value={name}>{name}</option>)}</select></label>
    </div>
    <div className="edge-explorer-count">{visible.length} produit{visible.length === 1 ? "" : "s"} trouvé{visible.length === 1 ? "" : "s"}</div>
    {warning && <p className="dashboard-warning">{warning}</p>}
    {visible.length ? <div className="edge-explorer-grid">{visible.map(card => <article key={card.productId} className="edge-explorer-tile">
      <Link href={`/explorer/${encodeURIComponent(card.productId)}`} className="edge-explorer-image" aria-label={`Voir la fiche de ${card.name}`}><AssetImage src={card.image} name={card.name}/></Link>
      <div className="edge-explorer-body"><span>{card.setName} · #{card.number}</span><h2>{card.name}</h2><p>{card.rarity}</p><strong>{card.low === null ? "Prix indisponible" : new Intl.NumberFormat("fr-FR", {style:"currency",currency:card.currency}).format(card.low)}</strong><small>Prix indicatif, pas une vente conclue · Langue et état à confirmer</small><Link href={`/explorer/${encodeURIComponent(card.productId)}`} className="edge-product-open">Voir la fiche →</Link></div>
    </article>)}</div> : <div className="edge-home-empty"><strong>Aucun produit correspondant</strong><p>Essayez une autre recherche ou série. Aucun résultat fictif n'est ajouté.</p></div>}
  </div>;
}
