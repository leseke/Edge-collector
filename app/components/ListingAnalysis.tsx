"use client";

import { useState } from "react";
import { summarizeCardLiquidity, type CardLiquidityEvidence } from "../lib/card-liquidity";
import { analyzeListing, estimateListingMarket, euroCents, resaleFeePercent } from "../lib/listing-analysis";

const format = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const euros = (cents: number) => format.format(cents / 100);

export function ListingAnalysis({ listingId, cards }: { listingId: string; cards: CardLiquidityEvidence[] }) {
  const [asking, setAsking] = useState("");
  const [fees, setFees] = useState("");
  const [variantKey, setVariantKey] = useState("");
  const [target, setTarget] = useState("");
  const [budget, setBudget] = useState("300");
  const askingCents = euroCents(asking);
  const acquisitionFeesCents = euroCents(fees);
  const evidence = cards.find(card => card.key === variantKey);
  const asOf = new Date().toISOString().slice(0, 10);
  const market = estimateListingMarket(evidence?.paidSales ?? [], asOf);
  const exitNetCents = market.conservativeNet;
  const targetGainCents = euroCents(target || "0");
  const budgetCents = euroCents(budget);
  const result = askingCents !== null && askingCents > 0 && targetGainCents !== null && budgetCents !== null
    ? analyzeListing({ askingCents, acquisitionFeesCents, exitNetCents, targetGainCents, budgetCents })
    : null;
  const longTerm = evidence ? summarizeCardLiquidity(evidence, asOf) : null;
  const historicalNet = market.historicalLow === null ? null :
    Math.floor(market.historicalLow * (100 - resaleFeePercent) / 100);
  const holdingGain = historicalNet === null || result?.cost == null ? null : historicalNet - result.cost;
  const fields = [
    ["asking", "Prix demandé (€)", asking, setAsking],
    ["fees", "Livraison et frais d’achat (€)", fees, setFees],
    ["target", "Gain net visé (€)", target, setTarget],
    ["budget", "Budget disponible (€)", budget, setBudget],
  ] as const;
  return <details>
    <summary>Analyser le prix</summary>
    <p>Renseigne le coût de l’annonce et confirme la variante exacte. EDGE calcule le repère de revente à partir des ventes documentées.</p>
    <label htmlFor={listingId + "-variant"}>Variante vérifiée dans l’annonce</label>{" "}
    <select id={listingId + "-variant"} value={variantKey} onChange={event => setVariantKey(event.target.value)}>
      <option value="">Variante inconnue ou absente du catalogue étudié</option>
      {cards.map(card => <option key={card.key} value={card.key}>
        {card.name} · {card.variant}
      </option>)}
    </select>
    <div className="dashboard-metrics">
      {fields.map(([name, label, value, setValue]) => <div key={name}>
        <label htmlFor={listingId + "-" + name}>{label}</label>{" "}
        <input id={listingId + "-" + name} inputMode="decimal" value={value}
          onChange={event => setValue(event.target.value)}
          aria-invalid={value !== "" && euroCents(value) === null} />
      </div>)}
    </div>
    <div role="status" aria-live="polite">
      {result && <>
        <p>{result.cost === null ? "Coût total à vérifier · frais d’achat manquants" : "Coût d’achat total · " + euros(result.cost)}</p>
        {result.budgetExceeded && <p>Budget dépassé. Piste à conserver en veille.</p>}
        {result.gain !== null && <p>Marge nette estimée · {euros(result.gain)}</p>}
        {result.maxAsk !== null && <p>Prix d’entrée maximal · {euros(result.maxAsk)}</p>}
        {result.gain !== null && <p>{result.budgetExceeded ? "Hors budget" :
          result.gain <= 0 || result.gain < (targetGainCents ?? 0) ? "Marge insuffisante à ce prix" : "Marge estimée compatible avec ton objectif"}.</p>}
      </>}
    </div>
    <h3>Court terme · 0 à 3 mois</h3>
    {market.conservativeGross === null || market.medianGross === null
      ? <p>{evidence ? "Veille · Moins de deux ventes comparables sur les 90 derniers jours." :
        "À identifier · Référence, langue, édition et état ou grade à confirmer."}</p>
      : <p>Revente brute indicative · {euros(market.conservativeGross)} à {euros(market.medianGross)} · {market.recent.length} ventes sur 90 jours.
        {" "}Le prix d’entrée utilise le bas de la fourchette et une hypothèse de {resaleFeePercent} % de frais de revente.</p>}
    <h3>Long terme · 1 an et plus</h3>
    {holdingGain !== null && holdingGain <= 0
      ? <p>Prix d’entrée fragile · Le bas des ventes historiques, net des frais estimés, ne couvre pas ton coût.</p>
      : longTerm?.signal === "SUPPLY_TIGHTENING" && holdingGain !== null
        ? <p>Pari à approfondir · Marge sur le scénario bas et raréfaction observée. Catalyseur et risque de baisse à vérifier.</p>
        : <p>Veille spéculative · {market.historicalLow === null ? "Historique comparable trop court ou trop mince." :
          "Aucun signal de raréfaction étayé dans les relevés disponibles."} Catalyseur à documenter.</p>}
    {market.historicalLow !== null && <p>Scénario de baisse · Retour au bas des ventes observées, {euros(market.historicalLow)} brut. Ce montant ne prédit pas le prix à un an.</p>}
    {market.history.length > 0 && <details>
      <summary>Ventes documentées · {market.history.length}</summary>
      <ul>{market.history.map(sale => <li key={sale.id}>
        <a href={sale.source} target="_blank" rel="noopener noreferrer">{euros(sale.cents)} · {sale.day} ↗</a>
      </li>)}</ul>
    </details>}
  </details>;
}
