import type { TcgCard } from "./market-data";

export function makeCorpus(card: TcgCard) {
  const parsed = new Date(card.observedAt);
  if (Number.isNaN(parsed.getTime()) || parsed.getTime() > Date.now()) throw new Error("Date de relevé invalide");
  const day = parsed.toISOString().slice(0, 10);
  const observed = parsed.toISOString();
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

