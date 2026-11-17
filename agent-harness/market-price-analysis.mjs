const priceKinds = new Set(["PRICE_CHANGE", "INDICATIVE_PRICE_CHANGE"]);
const sha256 = /^[a-f0-9]{64}$/;
const pricePattern = /^\d{1,9}(?:\.\d{1,2})?$/;

export function preparePriceAnalysis(report, { thresholdPercent = 10, maxEvents = 5 } = {}) {
  if (report?.schema !== "edge.commercial.events.v1" || !Array.isArray(report.events)) {
    throw new Error("invalid_commercial_events");
  }
  if (!Number.isFinite(thresholdPercent) || thresholdPercent <= 0 ||
      !Number.isSafeInteger(maxEvents) || maxEvents < 1 || maxEvents > 20) {
    throw new Error("invalid_analysis_limits");
  }
  const candidates = new Map();
  for (const event of report.events) {
    if (!event || !priceKinds.has(event.kind) || event.field !== "price" ||
        typeof event.id !== "string" || !sha256.test(event.id) ||
        typeof event.product_id !== "string" || !/^pokemon_card_[a-zA-Z0-9_.-]{1,100}$/.test(event.product_id) ||
        typeof event.before !== "string" || !pricePattern.test(event.before) ||
        typeof event.after !== "string" || !pricePattern.test(event.after) ||
        typeof event.evidence_sha256 !== "string" || !sha256.test(event.evidence_sha256) ||
        typeof event.previous_evidence_sha256 !== "string" || !sha256.test(event.previous_evidence_sha256) ||
        event.evidence_sha256 === event.previous_evidence_sha256) continue;

    if (typeof event.window_start !== "string" || typeof event.window_end !== "string") continue;
    const start = Date.parse(event.window_start);
    const end = Date.parse(event.window_end);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) continue;

    let source;
    try { source = new URL(event.source_url); } catch { continue; }
    if (source.protocol !== "https:" || source.username || source.password) continue;

    const before = Math.round(Number(event.before) * 100);
    const after = Math.round(Number(event.after) * 100);
    if (before <= 0 || after <= 0 || Math.abs(after - before) * 100 < thresholdPercent * before) continue;
    const changePercent = (after - before) * 100 / before;
    candidates.set(event.id, {
      eventId: event.id, productId: event.product_id, kind: event.kind,
      before: event.before, after: event.after,
      changePercent: Math.round(changePercent * 100) / 100,
      observedFrom: new Date(start).toISOString(), observedTo: new Date(end).toISOString(),
      source: source.href,
      previousEvidenceSha256: event.previous_evidence_sha256, evidenceSha256: event.evidence_sha256,
    });
  }
  return [...candidates.values()].sort((a, b) =>
    Math.abs(b.changePercent) - Math.abs(a.changePercent) || a.eventId.localeCompare(b.eventId)
  ).slice(0, maxEvents);
}

export async function analyzePriceChanges(report, { generate, thresholdPercent, maxEvents } = {}) {
  const candidates = preparePriceAnalysis(report, { thresholdPercent, maxEvents });
  if (generate === undefined) return { status: "DRY_RUN", candidates, analyses: [] };
  if (typeof generate !== "function") throw new Error("invalid_model_adapter");

  const analyses = [];
  for (const evidence of candidates) {
    try {
      const response = await generate({
        task: "ANALYZE_MARKET_PRICE_CHANGE", purchaseAuthorized: false, evidence: structuredClone(evidence),
      });
      if (typeof response !== "string" || Buffer.byteLength(response, "utf8") > 4_000) throw new Error();
      const analysis = JSON.parse(response);
      if (
        !analysis || analysis.eventId !== evidence.eventId ||
        typeof analysis.commentary !== "string" || !analysis.commentary.trim() ||
        analysis.commentary.length > 600 ||
        Object.keys(analysis).some(key => key !== "eventId" && key !== "commentary")
      ) throw new Error();
      analyses.push({ eventId: evidence.eventId, status: "UNREVIEWED", commentary: analysis.commentary.trim() });
    } catch {
      analyses.push({ eventId: evidence.eventId, status: "ANALYSIS_UNAVAILABLE" });
    }
  }
  return { status: "ANALYZED", candidates, analyses };
}
