import { NextRequest, NextResponse } from "next/server";
import { readCataloguePrice } from "../../../lib/catalogue-price";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const language = request.nextUrl.searchParams.get("lang") ?? "fr";
  const cardId = request.nextUrl.searchParams.get("id") ?? "";
  if (!["fr", "en", "ja"].includes(language) || !/^(?=.{2,50}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*$/.test(cardId)) {
    return NextResponse.json({ error: "Référence invalide" }, { status: 400 });
  }

  try {
    const source = `https://api.tcgdex.net/v2/${language}/cards/${encodeURIComponent(cardId)}`;
    const response = await fetch(source, { signal: AbortSignal.timeout(7000), next: { revalidate: 3600 } });
    if (response.status === 404) return NextResponse.json({ price: null });
    if (!response.ok || Number(response.headers.get("content-length") ?? 0) > 2_000_000) throw new Error();
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > 2_000_000) throw new Error();
    const card = JSON.parse(body);
    if (card?.id !== cardId) throw new Error();
    return NextResponse.json({ price: readCataloguePrice(card.pricing) }, {
      headers: { "Cache-Control": "public, max-age=60, s-maxage=300" },
    });
  } catch {
    return NextResponse.json({ error: "Prix temporairement indisponible" }, { status: 503 });
  }
}
