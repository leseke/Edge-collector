import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const LANGUAGES = new Set(["fr", "en", "ja"]);
const IMAGE_HOST = "assets.tcgdex.net";
type RecordValue = Record<string, unknown>;
function object(value: unknown): value is RecordValue { return !!value && typeof value === "object" && !Array.isArray(value); }
function imageUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== IMAGE_HOST || url.search || url.hash || !/^\/[a-zA-Z0-9_./-]+$/.test(url.pathname)) return null;
    return url.href;
  } catch { return null; }
}
async function upstream(url: string): Promise<unknown> {
  const response = await fetch(url, { signal: AbortSignal.timeout(7000), headers: { accept: "application/json" }, next: { revalidate: 3600 } });
  if (!response.ok) throw new Error("Upstream unavailable");
  if (Number(response.headers.get("content-length") ?? 0) > 2_000_000) throw new Error("Oversized response");
  const body = await response.text();
  if (new TextEncoder().encode(body).byteLength > 2_000_000) throw new Error("Oversized response");
  return JSON.parse(body) as unknown;
}
export async function GET(request: NextRequest) {
  const language = request.nextUrl.searchParams.get("lang") ?? "fr";
  const setId = request.nextUrl.searchParams.get("set");
  if (!LANGUAGES.has(language) || (setId !== null && !/^(?=.{2,40}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*$/.test(setId))) {
    return NextResponse.json({ error: "Paramètres invalides" }, { status: 400 });
  }
  try {
    const base = "https://api.tcgdex.net/v2/" + language + "/sets";
    if (setId !== null) {
      const data = await upstream(base + "/" + encodeURIComponent(setId));
      if (!object(data) || !Array.isArray(data.cards)) throw new Error("Invalid set");
      const cards = data.cards.slice(0, 120).filter(object).filter(card => typeof card.id === "string" && typeof card.name === "string")
        .map(card => ({ id: card.id, name: card.name, number: typeof card.localId === "string" ? card.localId : "", image: imageUrl(card.image), language, source: "TCGdex", price: null }));
      return NextResponse.json({ cards, set: { id: setId, name: typeof data.name === "string" ? data.name : setId }, source: "TCGdex", marketPricesIncluded: false });
    }
    const data = await upstream(base);
    if (!Array.isArray(data)) throw new Error("Invalid sets");
    const sets = data.slice(0, 500).filter(object).filter(set => typeof set.id === "string" && /^(?=.{2,40}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*$/.test(set.id) && typeof set.name === "string")
      .map(set => ({ id: set.id, name: set.name, logo: imageUrl(set.logo), cardCount: object(set.cardCount) && typeof set.cardCount.total === "number" ? set.cardCount.total : null }));
    return NextResponse.json({ sets, language, source: "TCGdex", marketPricesIncluded: false });
  } catch {
    return NextResponse.json({ error: "Extensions temporairement indisponibles" }, { status: 503 });
  }
}
