"use client";

import { useEffect, useState, type FormEvent } from "react";
import { cardmarketConditions, cardmarketOfferStorageKey, observedCardmarketOffer, readCardmarketOffers, type CardmarketOffer } from "../lib/cardmarket-offers";

const priceFormat = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "Europe/Paris" });

export function CardmarketOffers({ cardId, language }: { cardId: string; language: string }) {
  const key = cardmarketOfferStorageKey(cardId, language);
  const [offers, setOffers] = useState<CardmarketOffer[] | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    try {
      setOffers(readCardmarketOffers(localStorage.getItem(key)));
    } catch {
      setStatus("Le stockage local est indisponible.");
    }
  }, [key]);

  function recordOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!offers) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const offer = observedCardmarketOffer(String(values.get("source") ?? ""), String(values.get("price") ?? ""),
      String(values.get("condition") ?? ""), new Date().toISOString());
    if (!offer) {
      setStatus("Vérifie le lien de la carte, le prix en euros et l’état sélectionné.");
      return;
    }
    try {
      const history = readCardmarketOffers(localStorage.getItem(key));
      const next = [offer, ...history].slice(0, 20);
      localStorage.setItem(key, JSON.stringify(next));
      setOffers(next);
      form.reset();
      setStatus("Prix demandé enregistré.");
    } catch {
      setStatus("Le prix n’a pas pu être enregistré.");
    }
  }

  return <section className="edge-product-panel" aria-labelledby="cardmarket-offers-title">
    <h2 id="cardmarket-offers-title">Offres Cardmarket · {language.toUpperCase()}</h2>
    <p>Relevés manuels de prix demandés, hors livraison. Les 20 derniers sont conservés sur cet appareil.</p>
    <details>
      <summary>Relever une offre</summary>
      <p>Sur Cardmarket, vérifie la référence et le drapeau de la ligne d’offre avant de reporter le prix.</p>
      <p><a href="https://www.cardmarket.com/fr/Pokemon/Products" target="_blank" rel="noopener noreferrer">Ouvrir Cardmarket ↗</a></p>
      <form onSubmit={recordOffer}>
        <p><label>Lien de la fiche Cardmarket <input name="source" type="url" required maxLength={1000} /></label></p>
        <p><label>Prix demandé en euros <input name="price" inputMode="decimal" required maxLength={10} /></label></p>
        <p><label>État <select name="condition" required defaultValue="">
          <option value="" disabled>Choisir l’état</option>
          {cardmarketConditions.map(condition => <option key={condition}>{condition}</option>)}
        </select></label></p>
        <p><label><input type="checkbox" required /> La ligne d’offre correspond à cette carte et indique {language.toUpperCase()}.</label></p>
        <button type="submit" disabled={offers === null}>Enregistrer le prix demandé</button>
      </form>
    </details>
    <p role="status">{status}</p>
    {offers?.length ? <ul>{offers.map((offer, index) => <li key={offer.observedAt + ":" + index}>
      {priceFormat.format(offer.cents / 100)} · {offer.condition} · {dateFormat.format(new Date(offer.observedAt))} · <a href={offer.source}>Fiche Cardmarket ↗</a>
    </li>)}</ul> : <p>Aucun prix demandé relevé dans cette langue.</p>}
  </section>;
}
