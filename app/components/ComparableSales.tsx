"use client";

import { createContext, useContext, type ReactNode } from "react";
import { comparableSales } from "../lib/comparable-sales";
import type { SaleVariant } from "../lib/radar-paid-sales";

const PaidVariants = createContext<SaleVariant[]>([]);
export function PaidHistoryProvider({ variants, children }: { variants: SaleVariant[]; children: ReactNode }) {
  return <PaidVariants.Provider value={variants}>{children}</PaidVariants.Provider>;
}

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function ComparableSales({ cardKey, lotId }: { cardKey: string | null; lotId: string }) {
  const variants = useContext(PaidVariants);
  const history = comparableSales(variants, cardKey, lotId, new Date().toISOString().slice(0, 10));
  function list(rows: NonNullable<typeof history>["exact"], showVariant = false) {
    return <ul>{rows.map(row => <li key={row.id}>
      <a href={row.source} target="_blank" rel="noopener noreferrer"><strong>{euros.format(row.cents / 100)}</strong>
        {" · "}<time dateTime={row.day}>{date.format(new Date(row.day))}</time> · GCC ↗</a>
      {showVariant && <small>{row.variant}</small>}
    </li>)}</ul>;
  }
  return <section className="radar-comparables">
    <h4>Ventes comparables</h4>
    {!history ? <p>Les détails du lot ne permettent pas d’identifier sa variante avec certitude.</p> : <>
      {history.exact.length ? <>
        <p>{history.exact.length} vente{history.exact.length > 1 ? "s" : ""} payée{history.exact.length > 1 ? "s" : ""} de la même variante dans EDGE
          {history.median !== null && <> · Médiane <strong>{euros.format(history.median / 100)}</strong></>}</p>
        {list(history.exact.slice(0, 3))}
        {history.exact.length > 3 && <details><summary>Voir tout l’historique ({history.exact.length})</summary>{list(history.exact.slice(3))}</details>}
      </> : <p>Aucune autre vente payée de cette variante dans l’historique EDGE.</p>}
      {history.related.length > 0 && <details><summary>Autres variantes de la carte ({history.related.length})</summary>{list(history.related, true)}</details>}
    </>}
  </section>;
}
