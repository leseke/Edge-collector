"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import type { TcgCard } from "../lib/market-data";
import { AssetImage } from "../components/AssetImage";

type Category = "cards" | "sealed";
type Sort = "series" | "name" | "price-low" | "price-high";

function formatPrice(card: TcgCard): string {
  if (card.low === null || !Number.isFinite(card.low)) return "Prix indisponible";
  try { return new Intl.NumberFormat("fr-FR", { style: "currency", currency: card.currency }).format(card.low); }
  catch { return "Prix indisponible"; }
}

export function ExplorerGrid({ cards, warning }: { cards: TcgCard[]; warning: string | null }) {
  const [category, setCategory] = useState<Category>("cards");
  const [query, setQuery] = useState("");
  const [series, setSeries] = useState("ALL");
  const [sort, setSort] = useState<Sort>("series");
  const seriesGroups = useMemo(() => {
    const groups = new Map<string, TcgCard[]>();
    for (const card of cards) groups.set(card.setName, [...(groups.get(card.setName) ?? []), card]);
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, "fr"));
  }, [cards]);
  const visible = useMemo(() => {
    if (category === "sealed") return [];
    const term = query.trim().toLocaleLowerCase("fr");
    const filtered = cards.filter(card => (series === "ALL" || card.setName === series) &&
      [card.name, card.setName, card.number, card.rarity].some(value => value.toLocaleLowerCase("fr").includes(term)));
    return filtered.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name, "fr");
      if (sort === "price-low") return (a.low ?? Infinity) - (b.low ?? Infinity);
      if (sort === "price-high") return (b.low ?? -Infinity) - (a.low ?? -Infinity);
      return a.setName.localeCompare(b.setName, "fr") || a.number.localeCompare(b.number, "fr", { numeric: true });
    });
  }, [cards, category, query, series, sort]);

  return <div className="native-dashboard edge-explorer edge-explorer-v3">
    <p className="native-eyebrow">EDGE / EXPLORATION</p>
    <h1>Explorer les collections<span>.</span></h1>
    <p className="edge-explorer-intro">Découvre les produits suivis par EDGE et accède à leurs dossiers de marché. Les relevés sont partiels et ne constituent pas un catalogue exhaustif.</p>

    <div className="edge-explorer-tabs" role="group" aria-label="Type de produits">
      <button type="button" className={category === "cards" ? "active" : ""} aria-pressed={category === "cards"} onClick={() => setCategory("cards")}>Cartes <span>{cards.length}</span></button>
      <button type="button" className={category === "sealed" ? "active" : ""} aria-pressed={category === "sealed"} onClick={() => setCategory("sealed")}>Produits scellés <span>0</span></button>
    </div>

    {category === "cards" ? <>
      <div className="edge-explorer-filters edge-explorer-filters-v3">
        <label><span>Rechercher une carte ou une série</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Nom, numéro, extension…" /></label>
        <label><span>Série</span><select value={series} onChange={event => setSeries(event.target.value)}><option value="ALL">Toutes les séries</option>{seriesGroups.map(([name]) => <option key={name} value={name}>{name}</option>)}</select></label>
        <label><span>Trier par</span><select value={sort} onChange={event => { const value = event.currentTarget.value; if (value === "series" || value === "name" || value === "price-low" || value === "price-high") setSort(value); }}><option value="series">Série et numéro</option><option value="name">Nom A–Z</option><option value="price-low">Prix croissant</option><option value="price-high">Prix décroissant</option></select></label>
      </div>

      {series === "ALL" && !query.trim() && seriesGroups.length > 0 && <section className="edge-series-section" aria-label="Collections observées">
        <div className="edge-explorer-section-title"><h2>Collections observées</h2><span>{seriesGroups.length} série{seriesGroups.length > 1 ? "s" : ""}</span></div>
        <div className="edge-series-strip">{seriesGroups.map(([name, items]) => <button key={name} type="button" className="edge-series-card" onClick={() => setSeries(name)}>
          <span className="edge-series-art"><AssetImage src={items.find(item => item.image)?.image ?? null} name={name}/></span>
          <strong>{name}</strong><small>{items.length} carte{items.length > 1 ? "s" : ""} observée{items.length > 1 ? "s" : ""}</small>
        </button>)}</div>
      </section>}

      <div className="edge-explorer-section-title edge-explorer-results-heading"><h2>Cartes suivies</h2><span>{visible.length} résultat{visible.length > 1 ? "s" : ""}</span></div>
      {warning && <p className="dashboard-warning">{warning}</p>}
      {visible.length ? <div className="edge-explorer-grid">{visible.map(card => <article key={card.productId} className="edge-explorer-tile">
        <Link href={`/explorer/${encodeURIComponent(card.productId)}`} className="edge-explorer-image" aria-label={`Voir la fiche de ${card.name}`}><AssetImage src={card.image} name={card.name}/></Link>
        <div className="edge-explorer-body"><span>{card.setName} · #{card.number}</span><h2>{card.name}</h2><p>{card.rarity}</p><strong>{formatPrice(card)}</strong><small>Prix indicatif · Langue et état à confirmer · Pas une vente conclue</small><Link href={`/explorer/${encodeURIComponent(card.productId)}`} className="edge-product-open">Voir la fiche →</Link></div>
      </article>)}</div> : <div className="edge-home-empty"><strong>Aucune carte correspondante</strong><p>Modifie les filtres pour consulter les cartes réellement observées.</p><button type="button" className="edge-reset-filters" onClick={() => { setQuery(""); setSeries("ALL"); }}>Effacer les filtres</button></div>}
    </> : <section className="edge-sealed-empty" aria-live="polite">
      <span className="edge-sealed-symbol" aria-hidden="true">▣</span>
      <h2>Produits scellés</h2>
      <p>Cette catégorie est prévue pour les boosters, displays, ETB, coffrets et autres produits scellés. Aucun produit scellé n'est présent dans le relevé TCG vérifié utilisé ici.</p>
      <p className="edge-sealed-note">Nous n'affichons ni prix fictifs ni offres non vérifiées. La prochaine étape est de raccorder une source de catalogue distincte des observations de marché.</p>
      <button type="button" className="edge-reset-filters" onClick={() => setCategory("cards")}>Voir les cartes disponibles</button>
    </section>}
  </div>;
}
