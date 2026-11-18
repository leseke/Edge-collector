import { NextRequest, NextResponse } from "next/server";
import { catalogueLanguages } from "../../../lib/product-variant";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const LANGUAGES = new Set(Object.keys(catalogueLanguages));
const API = "https://api.tcgdex.net/v2";
const ASSETS = "https://assets.tcgdex.net/";
type TcgDexCard = { id?: unknown; localId?: unknown; name?: unknown; image?: unknown };
function safeImage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net" || url.search || url.hash) return null;
    const path = url.pathname.replace(/\/$/, "");
    if (!/^\/[a-z]{2}\/[a-zA-Z0-9_./-]+$/.test(path) || !LANGUAGES.has(path.split("/")[1])) return null;
    return /\/(high|low)\.(webp|png|jpg)$/.test(path) ? url.href : `${url.origin}${path}/high.webp`;
  } catch { return null; }
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  const language = request.nextUrl.searchParams.get("lang") ?? "fr";
  if (!LANGUAGES.has(language) || query.length < 2 || query.length > 60 || /[\u0000-\u001f]/.test(query)) {
    return NextResponse.json({ error: "Recherche invalide", cards: [] }, { status: 400 });
  }
  try {
    const url = new URL(`${API}/${language}/cards`);
    url.searchParams.set("name", query);
    const response = await fetch(url, { signal: AbortSignal.timeout(7000), headers: { accept: "application/json" }, next: { revalidate: 3600 } });
    if (!response.ok) throw new Error("TCGdex unavailable");
    const length = Number(response.headers.get("content-length") ?? 0);
    if (length > 2_000_000) throw new Error("Oversized response");
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > 2_000_000) throw new Error("Oversized response");
    const records: unknown = JSON.parse(body);
    if (!Array.isArray(records)) throw new Error("Invalid response");
    const cards = records.slice(0, 60).filter((item): item is TcgDexCard => item !== null && typeof item === "object" && !Array.isArray(item))
      .filter(item => typeof item.id === "string" && /^(?=.{2,50}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*$/.test(item.id) && typeof item.name === "string" && item.name.length <= 150)
      .map(item => ({ id: item.id as string, name: item.name as string, number: typeof item.localId === "string" ? item.localId : "", image: safeImage(item.image), language, source: "TCGdex", price: null }));
    return NextResponse.json({ cards, language, source: "TCGdex", marketPricesIncluded: false }, { headers: { "Cache-Control": "public, max-age=60, s-maxage=3600" } });
  } catch {
    return NextResponse.json({ error: "Catalogue temporairement indisponible", cards: [] }, { status: 503 });
  }
}
