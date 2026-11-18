"use client";

import { useState } from "react";
import { amountInCents, deliveredCost, type PurchaseBasis } from "../lib/delivered-cost";

const money = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const format = (cents: number) => money.format(cents / 100);

export function DeliveredCost({ basis, median }: { basis: PurchaseBasis; median: number | null }) {
  const [fees, setFees] = useState("");
  const [shipping, setShipping] = useState("");
  const [bid, setBid] = useState(basis.cents === null ? "" : (basis.cents / 100).toFixed(2).replace(".", ","));
  const auction = basis.kind === "auction";
  const price = auction ? amountInCents(bid) : basis.cents;
  const belowMinimum = auction && basis.cents !== null && price !== null && price < basis.cents;
  const total = belowMinimum ? null : deliveredCost(price, fees, shipping);
  const invalid = [fees, shipping, ...(auction ? [bid] : [])].some(value => value !== "" && amountInCents(value) === null);
  return <section className="radar-cost">
    <h4>Coût livré en France</h4>
    {auction ? <label>Enchère envisagée (€)
      <input inputMode="decimal" value={bid} onChange={event => setBid(event.target.value)} placeholder="Montant" />
    </label> : <p>Prix fixe GCC · {price === null ? "Indisponible" : format(price)}</p>}
    {auction && basis.cents !== null && <small>Prochaine enchère au dernier relevé · {format(basis.cents)}</small>}
    <p>Reporte les frais indiqués par GCC pour cet article. Entre 0 si la gratuité est confirmée.</p>
    <label>Frais acheteur (€)<input inputMode="decimal" placeholder="À confirmer" value={fees} onChange={event => setFees(event.target.value)} /></label>
    <label>Livraison, assurance et frais d’envoi compris (€)<input inputMode="decimal" placeholder="À confirmer" value={shipping} onChange={event => setShipping(event.target.value)} /></label>
    <div aria-live="polite">
      {invalid && <p>Utilise un montant positif ou nul avec deux décimales maximum.</p>}
      {belowMinimum && <p>L’enchère envisagée est inférieure au prochain palier relevé.</p>}
      <p><strong>Total livré · {total === null ? "À confirmer" : format(total)}</strong></p>
      {total !== null && median !== null && <p>{total === median ? "Au niveau de la médiane" :
        format(Math.abs(total - median)) + (total > median ? " au-dessus" : " en dessous") + " de la médiane"} des prix de vente ({format(median)}, livraison historique non vérifiée).</p>}
    </div>
    <small>Livraison depuis le Vault · Colissimo dès 12 €, assurance de 1 % de la valeur déclarée selon le barème GCC.</small>
    <a href="https://gradedcardcenter.com/tarifs" target="_blank" rel="noopener noreferrer">Consulter les tarifs GCC ↗</a>
  </section>;
}
