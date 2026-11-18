"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { SaleVariant } from "../lib/radar-paid-sales";
import { canonicalListingId } from "../lib/marketplace-captures";
import { ListingAnalysis } from "./ListingAnalysis";
import { leboncoinSearchUrl, leboncoinWatch } from "../lib/leboncoin-watch";

const storageKey = "edge.leboncoin.pistes.v1";

export function LeboncoinWatchPanel({ cards }: { cards: SaleVariant[] }) {
  const [links, setLinks] = useState<string[]>([]);
  const [value, setValue] = useState("");
  const [message, setMessage] = useState("");
  const [addedListing, setAddedListing] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(storageKey) ?? "[]");
      if (Array.isArray(saved)) {
        setLinks(saved.filter((url): url is string =>
          typeof url === "string" && !!canonicalListingId(url, "leboncoin")));
      }
    } catch {
      setMessage("Les liens enregistrés ne sont pas accessibles sur cet appareil.");
    }
    setReady(true);
  }, []);

  function addListing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = value.trim();
    const id = canonicalListingId(input, "leboncoin");
    if (!id) {
      setMessage("Colle le lien direct d’une annonce Leboncoin.");
      return;
    }
    if (links.some(link => canonicalListingId(link, "leboncoin") === id)) {
      setMessage("Cette annonce est déjà dans tes pistes.");
      return;
    }
    const url = new URL(input);
    const next = [...links, url.origin + url.pathname];
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setLinks(next);
      setAddedListing(url.origin + url.pathname);
      setValue("");
      setMessage("Annonce ajoutée aux pistes à vérifier.");
    } catch {
      setMessage("Impossible d’enregistrer cette annonce sur cet appareil.");
    }
  }

  function removeListing(url: string) {
    const next = links.filter(link => link !== url);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setLinks(next);
      setMessage("Piste retirée.");
    } catch {
      setMessage("Impossible de retirer cette piste sur cet appareil.");
    }
  }

  return <section id="analyse-annonce" className="dashboard-section radar-section" aria-labelledby="leboncoin-watch-title">
    <h2 id="leboncoin-watch-title">Analyser une annonce Leboncoin</h2>
    <p>Ajoute une annonce, confirme la variante et indique son prix avec les frais. EDGE utilise les ventes comparables pour estimer la revente quand les données le permettent.</p>
    <form className="radar-listing-form" onSubmit={addListing}>
      <label htmlFor="leboncoin-listing">Lien direct d’une annonce</label>{" "}
      <input id="leboncoin-listing" type="url" value={value} onChange={event => setValue(event.target.value)} required />{" "}
      <button type="submit" disabled={!ready}>Ajouter l’annonce</button>
    </form>
    <p className="radar-form-status" role="status">{message}</p>
    {links.length > 0 && <ul aria-label="Pistes à vérifier">{links.map(url => <li key={url}>
      <a href={url} target="_blank" rel="noopener noreferrer">Annonce {canonicalListingId(url, "leboncoin")?.split(":")[1]} ↗</a>{" "}
      <button type="button" onClick={() => removeListing(url)}>Retirer</button>
      <ListingAnalysis listingId={canonicalListingId(url, "leboncoin") ?? url} cards={cards} initiallyOpen={addedListing === url} />
    </li>)}</ul>}
    <small>Les annonces sont enregistrées sur cet appareil.</small>
    <details className="radar-disclosure">
      <summary>Recherches Leboncoin par série</summary>
      <ul>{leboncoinWatch.map(query => <li key={query}>
        <a href={leboncoinSearchUrl(query)} target="_blank" rel="noopener noreferrer">{query} ↗</a>
      </li>)}</ul>
    </details>
  </section>;
}
