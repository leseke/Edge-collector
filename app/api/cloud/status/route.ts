import { NextResponse } from "next/server";
import { getTcgMarketSnapshot } from "../../../lib/market-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const snapshot = await getTcgMarketSnapshot();
  const observedMs = snapshot.observedAt ? Date.parse(snapshot.observedAt) : NaN;
  const ageHours = Number.isFinite(observedMs) ? Math.max(0, (Date.now() - observedMs) / 3_600_000) : null;
  const freshness = ageHours === null ? "UNKNOWN" : ageHours <= 24 ? "FRESH" : ageHours <= 48 ? "AGING" : "STALE";
  const healthy = snapshot.status !== "UNAVAILABLE";
  return NextResponse.json({
    schema: "edge.cloud.readiness.v1",
    service: "edge-cloud-interface",
    source: "GitHub commercial-history, SHA-256 validated by EDGE",
    mode: "READ_ONLY",
    collection_running_in_worker: false,
    persistent_cloud_storage_configured: false,
    cloud_investigation_engine_configured: false,
    market: {
      status: snapshot.status,
      observed_at: snapshot.observedAt || null,
      freshness,
      age_hours: ageHours === null ? null : Math.round(ageHours * 10) / 10,
      displayed_cards: snapshot.cards.length,
      completed_sales_reported: snapshot.completedSales,
      reaction_cases: snapshot.reactionCaseCount,
      warning: snapshot.warning,
    },
    limitations: [
      "Listed or aggregated prices are not completed sales.",
      "No scheduled cloud collector or durable cloud history is configured.",
      "This endpoint does not provide investment recommendations.",
    ],
  }, { status: healthy ? 200 : 503, headers: { "Cache-Control": "no-store" } });
}
