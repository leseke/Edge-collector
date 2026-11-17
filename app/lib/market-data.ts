import { createHash } from "node:crypto";
import { marketVariant, type ProductVariant } from "./product-variant";

const DATA_BASE = "https://raw.githubusercontent.com/leseke/Edge-collector/edge/commercial-history/";
const encoder = new TextEncoder();

type Pointer = {
  schema: string;
  snapshot_id: string;
  observed_at: string;
  status: "OK" | "PARTIAL" | "FAILED" | "EMPTY";
  files: Record<string, { path: string; sha256: string }>;
};
type Observation = {
  id?: string;
  url?: string;
  product_id: string;
  seller: string;
  status: string;
  price?: string;
  currency?: string;
  price_kind: string;
  availability: string;
  observed_at: string;
  source_updated_at?: string;
  market_language_verified?: boolean;
  variant_evidence?: unknown;
  raw_file?: string;
  body_sha256?: string;
  completed_sale?: boolean;
};
type Report = { schema: string; observed_at: string; status: Pointer["status"]; observations: Observation[] };
type CardRecord = {
  id: string; name: string; localId: string; rarity?: string;
  set?: { name?: string; id?: string };
  image?: string; updated?: string;
  pricing?: { cardmarket?: { low?: number; avg?: number; trend?: number; updated?: string; unit?: string } };
};
export type TcgCard = {
  productId: string; name: string; setName: string; number: string; rarity: string;
  low: number | null; average: number | null; trend: number | null; currency: string;
  observedAt: string; sourceUpdatedAt: string | null; source: string;
  availability: string; languageVerified: boolean; priceKind: string; image: string | null;
  variant?: ProductVariant;
  priceChange?: PriceChange;
};
export type ReactionCaseSummary = { productId: string; publicationCount: number; reactionStatus: string; financialDecision: string; publications: { title: string; url: string; publishedAt: string; relationship: string }[] };
export type MarketSnapshot = {
  observedAt: string; status: string; cards: TcgCard[]; reactionCases: ReactionCaseSummary[];
  observationCount: number; successfulCount: number; failedCount: number;
  warning: string | null; reactionCaseCount: number; publishedEventCount: number; completedSales: number;
};

async function fetchText(url: string): Promise<string> {
  const response = await fetch(url, { cache: "no-store", headers: { accept: "application/json" }, signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error(`Market data unavailable (${response.status})`);
  const text = await response.text();
  if (encoder.encode(text).byteLength > 5_000_000) throw new Error("Market data exceeds size limit");
  return text;
}
function sha256(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}
function safeImage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try { const url = new URL(value); if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net" || url.search || url.hash) return null; const path = url.pathname.replace(/\/$/, ""); if (!/^\/(?:fr|en|ja|zh|de|es|it|pt|nl|ko|univ)\/[a-zA-Z0-9_/-]+$/.test(path)) return null; return /\/(?:high|low)\.(?:webp|png|jpg)$/.test(path) ? url.href : `${url.origin}${path}/high.webp`; }
  catch { return null; }
}
export type PriceChange = { before: number; after: number; percent: number; from: string; to: string; source: string };

export function readPriceChange(events: unknown[], observation: Observation): PriceChange | undefined {
  if (observation.status !== "OK" || !observation.id || !observation.url || !observation.body_sha256) return;
  for (const value of events) {
    if (!value || typeof value !== "object") continue;
    const event = value as Record<string, unknown>;
    if (event.kind !== "INDICATIVE_PRICE_CHANGE" || observation.price_kind !== "AGGREGATED_INDICATIVE_LOW" ||
        event.field !== "price" || event.observation_id !== observation.id ||
        event.product_id !== observation.product_id || event.source_url !== observation.url ||
        event.evidence_sha256 !== observation.body_sha256 || event.window_end !== observation.observed_at ||
        typeof event.previous_evidence_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(event.previous_evidence_sha256) ||
        typeof event.window_start !== "string" || !(Date.parse(event.window_start) < Date.parse(observation.observed_at)) ||
        typeof event.before !== "string" || typeof event.after !== "string" || event.after !== observation.price ||
        !/^\d{1,9}(?:\.\d{1,2})?$/.test(event.before) || !/^\d{1,9}(?:\.\d{1,2})?$/.test(event.after)) continue;
    const before = Number(event.before);
    const after = Number(event.after);
    if (before <= 0 || after <= 0 || before === after) continue;
    try {
      const source = new URL(observation.url);
      if (source.protocol === "https:" && !source.username && !source.password) {
        return { before, after, percent: (after - before) / before, from: event.window_start, to: observation.observed_at, source: source.href };
      }
    } catch { return; }
  }
}

async function readSnapshotEvents(pointer: Pointer): Promise<unknown[]> {
  try {
    const path = `snapshots/${pointer.snapshot_id}/events.json`;
    const entry = pointer.files["events.json"];
    if (entry && entry.path !== path) return [];
    const legacyManifest = entry ? null : JSON.parse(await fetchText(DATA_BASE + `snapshots/${pointer.snapshot_id}/manifest.json`));
    const expected = entry ? entry.sha256 : legacyManifest?.["events.json"];
    if (typeof expected !== "string" || !/^[a-f0-9]{64}$/.test(expected)) return [];
    const raw = await fetchText(DATA_BASE + path);
    if (sha256(raw) !== expected) return [];
    const doc = JSON.parse(raw);
    return doc?.schema === "edge.commercial.events.v1" && Array.isArray(doc.events) ? doc.events : [];
  } catch { return []; }
}

export async function getTcgMarketSnapshot(): Promise<MarketSnapshot> {
  try {
    const pointerText = await fetchText(DATA_BASE + "latest.json");
    const pointer = JSON.parse(pointerText) as Pointer;
    if (pointer.schema !== "edge.public.live_capture.v1" || !/^\d+-\d+$/.test(pointer.snapshot_id) || !pointer.files || typeof pointer.files !== "object") throw new Error("Invalid snapshot pointer");
    const reportEntry = pointer.files["report.json"];
    if (!reportEntry || reportEntry.path !== `snapshots/${pointer.snapshot_id}/report.json` || !/^[a-f0-9]{64}$/.test(reportEntry.sha256)) throw new Error("Invalid report reference");
    const reportText = await fetchText(DATA_BASE + reportEntry.path);
    if (sha256(reportText) !== reportEntry.sha256) throw new Error("Report integrity check failed");
    const report = JSON.parse(reportText) as Report;
    if (report.schema !== "edge.commercial.snapshot.v1" || report.observed_at !== pointer.observed_at || report.status !== pointer.status || !Array.isArray(report.observations)) throw new Error("Invalid report schema");
    const mriEntry = pointer.files["mri_cases.json"];
    if (!mriEntry || mriEntry.path !== `snapshots/${pointer.snapshot_id}/mri_cases.json` || !/^[a-f0-9]{64}$/.test(mriEntry.sha256)) throw new Error("Invalid MRI reference");
    const mriText = await fetchText(DATA_BASE + mriEntry.path);
    if (sha256(mriText) !== mriEntry.sha256) throw new Error("MRI integrity check failed");
    const mri = JSON.parse(mriText) as { schema: string; cases: Array<{ product_id: string; reaction_status?: string; financial_decision?: string; publication_evidence?: Array<{ title?: string; source_url?: string; published_at?: string; relationship?: string }> }> };
    if (mri.schema !== "edge.mri.multi_source_cases.v1" || !Array.isArray(mri.cases)) throw new Error("Invalid MRI schema");
    const tcgCases = mri.cases.filter((item) => item.product_id?.startsWith("pokemon_card_"));
    const reactionCases: ReactionCaseSummary[] = mri.cases.filter(item => typeof item.product_id === "string" && /^[a-z0-9_-]{3,110}$/.test(item.product_id)).map(item => ({
      productId: item.product_id, publicationCount: Array.isArray(item.publication_evidence) ? item.publication_evidence.length : 0,
      reactionStatus: item.reaction_status || "NON_DOCUMENTÉ", financialDecision: item.financial_decision || "NOT_ESTABLISHED",
      publications: (Array.isArray(item.publication_evidence) ? item.publication_evidence : []).filter(e => typeof e.title === "string" && typeof e.source_url === "string" && /^https:\/\//.test(e.source_url)).slice(0, 5).map(e => ({ title: e.title!, url: e.source_url!, publishedAt: e.published_at || "", relationship: e.relationship || "LIEN_NON_VÉRIFIÉ" }))
    }));
    const observations = report.observations.filter((item) => item.product_id?.startsWith("pokemon_card_") && item.raw_file && item.body_sha256);
    const eventsPromise = readSnapshotEvents(pointer);
    const cards = await Promise.all(observations.map(async (item): Promise<TcgCard | null> => {
      try {
        if (!/^[a-zA-Z0-9_.-]+\.json$/.test(item.raw_file!)) return null;
        const rawText = await fetchText(DATA_BASE + `snapshots/${pointer.snapshot_id}/${item.raw_file}`);
        if (sha256(rawText) !== item.body_sha256) return null;
        const card = JSON.parse(rawText) as CardRecord;
        const pricing = card.pricing?.cardmarket;
        const price = Number(item.price);
        return {
          productId: item.product_id, name: card.name || item.product_id, setName: card.set?.name || "Série non renseignée",
          number: card.localId || "—", rarity: card.rarity || "Rareté non renseignée",
          low: item.status === "OK" && Number.isFinite(price) && price > 0 ? price : null,
          average: typeof pricing?.avg === "number" ? pricing.avg : null,
          trend: typeof pricing?.trend === "number" ? pricing.trend : null,
          currency: item.currency || pricing?.unit || "EUR", observedAt: item.observed_at,
          sourceUpdatedAt: item.source_updated_at || pricing?.updated || null, source: item.seller,
          availability: item.availability, languageVerified: item.market_language_verified === true,
          priceKind: item.price_kind, image: safeImage(card.image),
          priceChange: readPriceChange(await eventsPromise, item),
          variant: marketVariant(item.status === "OK" ? item.variant_evidence : undefined),
        };
      } catch { return null; }
    }));
    return {
      observedAt: report.observed_at, status: report.status, reactionCases, cards: cards.filter((card): card is TcgCard => card !== null),
      observationCount: observations.length, successfulCount: observations.filter((item) => item.status === "OK").length,
      failedCount: observations.filter((item) => item.status !== "OK").length,
      warning: report.status === "PARTIAL" ? "Collecte partielle : certaines sources n’ont pas répondu." : null,
      reactionCaseCount: tcgCases.length,
      publishedEventCount: tcgCases.reduce((total, item) => total + (item.publication_evidence?.length ?? 0), 0),
      completedSales: report.observations.filter((item) => item.product_id?.startsWith("pokemon_card_") && item.completed_sale === true).length,
    };
  } catch {
    return { observedAt: "", status: "UNAVAILABLE", cards: [], reactionCases: [], observationCount: 0, successfulCount: 0, failedCount: 0, warning: "Le dernier relevé vérifiable n’a pas pu être chargé. Aucun prix n’est affiché comme actuel.", reactionCaseCount: 0, publishedEventCount: 0, completedSales: 0 };
  }
}
