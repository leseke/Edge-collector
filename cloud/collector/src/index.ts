import { parseIndicativePrice } from "./parse.mjs";
import { readBoundedText } from "./bounded.mjs";
// EDGE Cloud Collector — isolated Worker, not wired into the deployed Next.js app.
// Explicit deployment and cron enablement are required after D1 provisioning.
interface Env {
  DB: D1Database;
  TRIGGER_SECRET?: string;
}
type Target = { productId: string; url: string };
const TARGETS: readonly Target[] = [
  { productId: "pokemon_card_base1_4", url: "https://api.tcgdex.net/v2/fr/cards/base1-4" },
  { productId: "pokemon_card_swsh3_136", url: "https://api.tcgdex.net/v2/fr/cards/swsh3-136" },
];
const MAX_BYTES = 128_000;
const SOURCE = "TCGdex/Cardmarket indicative aggregate";
const ISO = () => new Date().toISOString();
const hex = (bytes: ArrayBuffer) => [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2,"0")).join("");
async function sha256(raw: string): Promise<string> {
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw)));
}
async function fetchTarget(target: Target): Promise<{raw: string; price: number | null; updated: string | null}> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);
  try {
    const response = await fetch(target.url, { signal: controller.signal, headers: { Accept: "application/json" }, redirect: "error" });
    if (!response.ok) throw new Error("upstream_" + response.status);
    const raw = await readBoundedText(response, MAX_BYTES);
    const parsed = parseIndicativePrice(raw);
    return { raw, price: parsed.price, updated: parsed.updated };
  } finally { clearTimeout(timeout); }
}
export async function collect(env: Env): Promise<void> {
  const started = ISO();
  const runId = crypto.randomUUID();
  await env.DB.prepare("INSERT INTO collection_runs (run_id,started_at,status) VALUES (?,?,?)").bind(runId,started,"RUNNING").run();
  let succeeded = 0, failed = 0;
  for (const target of TARGETS) {
    try {
      const result = await fetchTarget(target);
      const observedAt = ISO();
      const digest = await sha256(result.raw);
      // Aggregated price != completed sale. No claim of stock availability.
      await env.DB.prepare(`INSERT INTO observations
        (observation_id,run_id,product_id,source,observed_at,price_cents,currency,availability,price_kind,source_url,payload_sha256,source_updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`)
        .bind(crypto.randomUUID(),runId,target.productId,SOURCE,observedAt,result.price,
          result.price === null ? null : "EUR","UNKNOWN","AGGREGATE",target.url,digest,result.updated).run();
      succeeded++;
    } catch (error) {
      failed++;
      const rawReason = error instanceof Error ? error.message : "unknown";
      const reasonCode = /^(upstream_[0-9]{3}|oversize|invalid_[a-z_]+|no_cardmarket_pricing|AbortError)$/.test(rawReason) ? rawReason : "unexpected_failure";
      await env.DB.prepare("INSERT INTO collection_errors(error_id,run_id,product_id,source_url,occurred_at,reason_code) VALUES (?,?,?,?,?,?)")
        .bind(crypto.randomUUID(),runId,target.productId,target.url,ISO(),reasonCode).run();
      console.error("collector_target_failed", { runId, productId: target.productId, reason: reasonCode });
    }
  }
  const status = succeeded === 0 ? "FAILED" : failed > 0 ? "PARTIAL" : "OK";
  await env.DB.prepare("UPDATE collection_runs SET finished_at=?,status=?,attempted=?,succeeded=?,failed=? WHERE run_id=?")
    .bind(ISO(),status,TARGETS.length,succeeded,failed,runId).run();
}
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/internal/collect") {
      const supplied = request.headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
      if (!env.TRIGGER_SECRET || !supplied || (await sha256(supplied)) !== (await sha256(env.TRIGGER_SECRET))) {
        return Response.json({ error: "not_found" }, { status: 404 });
      }
      await collect(env);
      return Response.json({ service: "edge-tcg-collector", collection: "completed" });
    }
    return Response.json({ service: "edge-tcg-collector", mode: "NO_PUBLIC_DATA", status: "CONFIGURATION_REQUIRED" }, { status: 503 });
  },
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(collect(env));
  },
};
