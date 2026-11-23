"use client";

import type { TcgCard } from "../lib/market-data";

function makeCorpus(card: TcgCard) {
  const day = new Date(card.observedAt).toISOString().slice(0, 10);
  const observed = new Date(card.observedAt).toISOString();
  const sourceId = "src_capture";
  const hasPrice = card.low !== null && Number.isFinite(card.low) && card.low > 0;
  const datasetId = "ds_indicative";
  const sourceUrl = `https://raw.githubusercontent.com/leseke/Edge-collector/edge/commercial-history/snapshots/${card.snapshotId}/report.json`;
  return {
    corpus_schema: "edge.corpus.v1",
    corpus_id: `tcg_${card.snapshotId.replace(/[^a-z0-9_.-]/gi, "_").toLowerCase()}`.slice(0, 64),
    simulated: false,
    data_as_of: observed,
    subject: { title: card.name, market: "TCG", category: "tcg", region: "GLOBAL" },
    entities: [card.name],
    topics: [{ topic_id: "market_evidence", question: "Quelles observations sont disponibles et quelles preuves manquent ?", keywords: ["TCG", "prix", "provenance"] }],
    sources: [{
      source_id: sourceId,
      title: `Relevé commercial EDGE ${card.snapshotId}`,
      publisher: "EDGE — collecte déclarée",
      url: sourceUrl,
      published_at: null,
      accessed_at: day,
      tier: "unverified",
      simulated: false,
      notes: `Source déclarée : ${card.source}. Rapport SHA-256 : ${card.reportSha256}. Données brutes SHA-256 : ${card.rawSha256}. Ces empreintes contrôlent l'intégrité, pas la véracité des prix.`,
    }],
    datasets: hasPrice ? [{
      dataset_id: datasetId,
      title: "Indication basse agrégée non vérifiée (pas une vente conclue)",
      unit: "currency",
      currency: card.currency,
      measure: "other",
      territory: "GLOBAL",
      period: { start: day, end: day },
      frequency: "irregular",
      provenance: { source_ids: [sourceId], method: `Indication agrégée déclarée : ${card.priceKind || "nature non renseignée"}. Aucune preuve de transaction.`, collected_by: "collector" },
      simulated: false,
      points: [{ t: day, value: card.low, status: "estimated" }],
    }] : [],
    dataset_topics: hasPrice ? { [datasetId]: ["market_evidence"] } : {},
    extracts: [],
  };
}

export function TcgCorpusDownload({ card }: { card: TcgCard }) {
  function download() {
    const corpus = makeCorpus(card);
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
  return <div><button className="tcg-investigate-link" type="button" onClick={download}>Exporter un corpus EDGE (JSON)</button><p>Corpus non simulé fondé sur le relevé, à valider par le compagnon local. Aucune vente conclue ni preuve indépendante ajoutée.</p></div>;
}
