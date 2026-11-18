"use client";

import { useState } from "react";
import { analyzeListing, euroCents } from "../lib/listing-analysis";

const format = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const euros = (cents: number) => format.format(cents / 100);

export function ListingAnalysis({ listingId }: { listingId: string }) {
  const [asking, setAsking] = useState("");
  const [fees, setFees] = useState("");
  const [exit, setExit] = useState("");
  const [target, setTarget] = useState("");
  const [budget, setBudget] = useState("300");
  const askingCents = euroCents(asking);
  const acquisitionFeesCents = euroCents(fees);
  const exitNetCents = euroCents(exit);
  const targetGainCents = euroCents(target || "0");
  const budgetCents = euroCents(budget);
  const result = askingCents !== null && askingCents > 0 && targetGainCents !== null && budgetCents !== null
    ? analyzeListing({ askingCents, acquisitionFeesCents, exitNetCents, targetGainCents, budgetCents })
    : null;
  const fields = [
    ["asking", "Prix demandé (€)", asking, setAsking],
    ["fees", "Livraison et frais d’achat (€)", fees, setFees],
    ["exit", "Hypothèse de revente nette (€)", exit, setExit],
    ["target", "Gain net visé (€)", target, setTarget],
    ["budget", "Budget disponible (€)", budget, setBudget],
  ] as const;
  return <details>
    <summary>Analyser le prix</summary>
    <p>Renseigne les montants affichés par l’annonce. Pour la revente, utilise un montant net après frais et compare la même référence, la langue, l’édition et l’état ou le grade.</p>
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
        {result.gain !== null && <p>Gain net selon ton hypothèse · {euros(result.gain)}</p>}
        {result.maxAsk !== null && <p>Prix demandé maximal selon ton hypothèse · {euros(result.maxAsk)}</p>}
        {result.maxAsk === null && <p>Le prix maximal exige une hypothèse de revente nette et les frais d’achat.</p>}
      </>}
    </div>
  </details>;
}
