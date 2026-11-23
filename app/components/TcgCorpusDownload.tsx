"use client";

import type { TcgCard } from "../lib/market-data";
import { useRouter } from "next/navigation";
import { makeCorpus } from "../lib/tcg-corpus";

const TRANSFER_KEY = "edge.local.pending-corpus.v1";

export function TcgCorpusDownload({ card }: { card: TcgCard }) {
  const router = useRouter();
  function prepareLocalInquiry() {
    try {
      const corpus = makeCorpus(card);
      const raw = JSON.stringify({ productId: card.productId, corpus });
      if (new TextEncoder().encode(raw).byteLength > 5 * 1024 * 1024) throw new Error("Corpus trop volumineux");
      window.sessionStorage.setItem(TRANSFER_KEY, raw);
      router.push(`/local?product=${encodeURIComponent(card.productId)}&name=${encodeURIComponent(card.name)}`);
    } catch {
      window.alert("Transfert impossible : vérifie la date du relevé et les paramètres de ton navigateur. L’export JSON reste disponible.");
    }
  }
  function download() {
    let corpus;
    try { corpus = makeCorpus(card); }
    catch { window.alert("Export impossible : date de relevé invalide."); return; }
    const blob = new Blob([JSON.stringify(corpus, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `edge-corpus-${card.snapshotId.replace(/[^a-zA-Z0-9_.-]/g, "_")}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }
  return <div><button className="tcg-investigate-link" type="button" onClick={prepareLocalInquiry}>Préparer l’enquête avec ce corpus</button><button className="tcg-investigate-link" type="button" onClick={download}>Exporter un corpus EDGE (JSON)</button><p>Corpus non simulé fondé sur le relevé, à valider par le compagnon local. Aucune vente conclue ni preuve indépendante ajoutée.</p></div>;
}
