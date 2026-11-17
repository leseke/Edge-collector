"use client";

import { useEffect, useRef, useState } from "react";
import type { CataloguePrice } from "../lib/catalogue-price";

const euro = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "Europe/Paris" });

export function CatalogueTilePrice({ language, cardId }: { language: string; cardId: string }) {
  const element = useRef<HTMLSpanElement>(null);
  const [result, setResult] = useState<CataloguePrice | null | "ERROR" | undefined>(undefined);

  useEffect(() => {
    const target = element.current;
    if (!target) return;
    const controller = new AbortController();

    function loadPrice() {
      const query = new URLSearchParams({ lang: language, id: cardId });
      fetch("/api/catalog/price?" + query, { signal: controller.signal })
        .then(async response => {
          if (!response.ok) throw new Error();
          const data: { price: CataloguePrice | null } = await response.json();
          if (!controller.signal.aborted) setResult(data.price);
        })
        .catch(() => {
          if (!controller.signal.aborted) setResult("ERROR");
        });
    }

    if (typeof IntersectionObserver === "undefined") {
      loadPrice();
      return () => controller.abort();
    }

    const observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting)) return;
      observer.disconnect();
      loadPrice();
    }, { rootMargin: "160px" });
    observer.observe(target);
    return () => {
      observer.disconnect();
      controller.abort();
    };
  }, [language, cardId]);

  return <span ref={element}>
    {result === undefined ? "Consultation du prix…" :
      result === "ERROR" ? "Prix temporairement indisponible" :
      result === null ? "Aucun prix indicatif disponible" :
      <>
        <strong>{euro.format(result.low)}</strong>
        <small>Prix bas indicatif · Cardmarket via TCGdex · <time dateTime={result.updatedAt}>{date.format(new Date(result.updatedAt))}</time>{result.stale ? " · Plus de 48 h" : ""}</small>
      </>}
  </span>;
}
