"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AssetImage } from "../components/AssetImage";
import { catalogueLanguages, isCatalogueLanguage } from "../lib/product-variant";
import { CatalogueTilePrice } from "./CatalogueTilePrice";

type Entry = { id: string; name: string; logo: string | null; cardCount: number | null };
type Card = { id: string; number: string; name: string; image: string | null };
const flags: Record<string,string> = { fr: "🇫🇷", en: "🇬🇧", ja: "🇯🇵", it: "🇮🇹" };

function useList<T>(url: string, field: "entries" | "cards", delay = 0) {
  const [result, setResult] = useState<{ url: string; items: T[]; error: boolean }>();
  useEffect(() => {
    if (!url) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error();
        const list = (await res.json())[field];
        if (!Array.isArray(list)) throw new Error();
        if (!controller.signal.aborted) setResult({ url, items: list, error: false });
      } catch {
        if (!controller.signal.aborted) setResult({ url, items: [], error: true });
      }
    }, delay);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [url, field, delay]);
  return result?.url === url ? result : undefined;
}

function Logo({ entry }: { entry: Entry }) {
  return entry.logo ? <img src={entry.logo.replace(/(?:\.(?:webp|png|jpg))?$/, ".webp")} alt="" loading="lazy"
    onError={e => { e.currentTarget.hidden = true; }} /> : null;
}

export function SeriesBrowser({ initialQuery }: { initialQuery: string }) {
  const params = useSearchParams();
  const lang = params.get("lang") ?? "fr";
  const language = isCatalogueLanguage(lang) ? lang : "fr";
  const family = params.get("family") ?? "";
  const set = params.get("set") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [filter, setFilter] = useState("");
  const term = query.trim();
  const base = "/api/catalog/sets?lang=" + language;
  const series = useList<Entry>(base + "&series=", "entries");
  const extensions = useList<Entry>(family ? base + "&series=" + encodeURIComponent(family) : "", "entries");
  const results = useList<Card>(set ? base + "&set=" + encodeURIComponent(set) : term.length >= 2 ?
    "/api/catalog/cards?lang=" + language + "&q=" + encodeURIComponent(term) : "", "cards", set ? 0 : 350);
  function navigate(values: Record<string,string>) {
    const url = new URL(window.location.href);
    for (const [key,value] of Object.entries(values)) {
      if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
    }
    window.history.pushState(null,"",url);
    setFilter("");
  }
  const selected = extensions?.items.find(x => x.id === set);
  const seriesName = series?.items.find(x => x.id === family)?.name;
  const needle = filter.trim().toLocaleLowerCase("fr").replace(/^#/, "");
  const cards = results?.items.filter(c => !set || c.name.toLocaleLowerCase("fr").includes(needle) || c.number.toLowerCase().includes(needle));
  return <section className="series-browser">
    {set && <header><button className="series-back" onClick={() => navigate({set:""})}>← {seriesName ?? "Extensions"}</button><h2>{selected?.name ?? set}</h2></header>}
    <input className="series-search" type="search" aria-label={set ? "Rechercher dans cette extension" : "Rechercher une carte"} placeholder={set ? "Nom ou numéro dans cette extension" : "Rechercher une carte par nom"}
      value={set ? filter : query} maxLength={60} onChange={e => set ? setFilter(e.target.value) : setQuery(e.target.value)} />
    <div className="series-languages" role="group" aria-label="Langue du catalogue">{Object.entries(catalogueLanguages).map(([id,label]) =>
      <button key={id} aria-label={label} aria-pressed={id === language} onClick={() => navigate({lang:id,family:"",set:""})}>{flags[id]} <small>{id.toUpperCase()}</small></button>)}</div>
    {set || term.length >= 2 ? <>
      {!set && <h2>Résultats de recherche</h2>}
      <p role="status">{!results ? "Chargement des cartes…" : results.error ? "Cartes temporairement indisponibles." : cards?.length + " carte(s) affichée(s)"}</p>
      <div className="series-card-grid">{cards?.map(card => <Link key={card.id} href={"/explorer/catalogue/" + language + "/" + encodeURIComponent(card.id) + "?" + new URLSearchParams({q:query, family, set})}>
        <div className="series-card-art"><AssetImage src={card.image} name={card.name} catalogueId={card.id} catalogueLanguage={language}/></div>
        <strong>{card.name}</strong><small>#{card.number || card.id}</small><CatalogueTilePrice language={language} cardId={card.id} />
      </Link>)}</div>
    </> : <>
      <h2>Toutes les séries</h2>
      {!series || series.error || !series.items.length ? <p role="status">{!series ? "Chargement des séries…" : series.error ? "Séries temporairement indisponibles." : "Aucune série disponible dans cette langue."}</p> :
      [...series.items].reverse().map(entry => <div className="series-family" key={entry.id}>
        <button className="series-row" aria-expanded={family === entry.id} onClick={() => navigate({family:family === entry.id ? "" : entry.id})}>
          <Logo entry={entry}/><strong>{entry.name}</strong><span aria-hidden="true">{family === entry.id ? "⌄" : "›"}</span>
        </button>
        {family === entry.id && (!extensions || extensions.error || !extensions.items.length ?
          <p role="status">{!extensions ? "Chargement des extensions…" : extensions.error ? "Extensions temporairement indisponibles." : "Aucune extension répertoriée."}</p> :
          <div className="series-sets">{[...extensions.items].reverse().map(ext => <button key={ext.id} onClick={() => navigate({set:ext.id})}>
            <Logo entry={ext}/><strong>{ext.name}</strong>{ext.cardCount !== null && <small>{ext.cardCount} cartes</small>}
          </button>)}</div>)}
      </div>)}
    </>}
  </section>;
}
