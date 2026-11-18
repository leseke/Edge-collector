import { colissimoStartingCents, estimateDeliveredCost, type PurchaseBasis } from "../lib/delivered-cost";

const money = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const format = (cents: number) => money.format(cents / 100);

export function DeliveredCost({ basis, median }: { basis: PurchaseBasis; median: number | null }) {
  const price = basis.cents;
  const cost = estimateDeliveredCost(price);
  const label = basis.kind === "auction" ? "Prochaine enchère au dernier relevé" : "Prix fixe GCC";
  return <section className="radar-cost">
    <h4>Coût livré en France</h4>
    {price !== null && cost ? <>
      <p><strong>Estimation Colissimo · {format(cost.estimate)}</strong></p>
      <p>{label} · {format(price)}</p>
      <p>Envoi individuel au tarif de départ · {format(colissimoStartingCents)}.
        Assurance estimée · {format(cost.insurance)} (1 % du prix retenu comme valeur déclarée).</p>
      <small>Le port final et les éventuels frais acheteur peuvent modifier cette estimation.</small>
      {median !== null && <p>Médiane des ventes · {format(median)}.
        {" "}{price === median ? "Le prix du lot correspond à la médiane." :
          "Le prix du lot est " + format(Math.abs(price - median)) + (price > median ? " au-dessus" : " en dessous") + " de la médiane, hors livraison."}</p>}
    </> : <p>{label} indisponible. Le coût livré ne peut pas encore être estimé.</p>}
    <a href="https://gradedcardcenter.com/tarifs" target="_blank" rel="noopener noreferrer">Barème GCC ↗</a>
  </section>;
}
