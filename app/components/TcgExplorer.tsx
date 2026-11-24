"use client";
import { useMemo, useState, type ReactNode } from "react";
import type { TcgCard } from "../lib/market-data";
import { filterCards, type ExplorerSort } from "../lib/tcg-explorer";
export function TcgExplorer({cards,tiles}:{cards:TcgCard[];tiles:ReactNode[]}) {
  const [query,setQuery]=useState("");
  const [series,setSeries]=useState("");
  const [sort,setSort]=useState<ExplorerSort>("name");
  const [limit,setLimit]=useState(24);
  const sets=useMemo(()=>Array.from(new Set(cards.map(c=>c.setName))).sort((a,b)=>a.localeCompare(b,"fr")),[cards]);
  const results=useMemo(()=>filterCards(cards,query,series,sort),[cards,query,series,sort]);
  const positions=useMemo(()=>new Map(cards.map((c,i)=>[c,i])),[cards]);
  if (!cards.length) return <div className="dashboard-empty">Aucune observation TCG vérifiable n’est disponible dans le dernier relevé.</div>;
  return <>
    <div className="tcg-explorer-controls">
      <label>Rechercher<input type="search" value={query} placeholder="Nom, numéro, rareté…" onChange={e=>{setQuery(e.target.value);setLimit(24);}} /></label>
      <label>Série<select value={series} onChange={e=>{setSeries(e.target.value);setLimit(24);}}><option value="">Toutes les séries</option>{sets.map(s=><option key={s}>{s}</option>)}</select></label>
      <label>Trier<select value={sort} onChange={e=>{setSort(e.target.value as ExplorerSort);setLimit(24);}}><option value="name">Nom</option><option value="low">Prix indicatif croissant par devise</option><option value="high">Prix indicatif décroissant par devise</option></select></label>
      <button type="button" onClick={()=>{setQuery("");setSeries("");setSort("name");setLimit(24);}}>Réinitialiser</button>
    </div>
    <p className="tcg-explorer-count" role="status">{results.length} / {cards.length} observations du dernier relevé · catalogue partiel</p>
    {results.length ? <div className="tcg-card-grid">{results.slice(0,limit).map(c=>tiles[positions.get(c)!])}</div> : <div className="dashboard-empty">Aucun résultat pour ces filtres.</div>}
    {results.length>limit && <button className="tcg-explorer-more" type="button" onClick={()=>setLimit(n=>n+24)}>Afficher 24 observations supplémentaires</button>}
    <p className="data-limit">Offres actives et ventes conclues : couverture non établie pour ces fiches. Les prix indicatifs ne sont pas des transactions.</p>
  </>;
}
