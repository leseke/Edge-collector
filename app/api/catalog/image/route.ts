import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const cardId = request.nextUrl.searchParams.get("id") ?? "";
  if (!/^(?=.{2,50}$)[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*$/.test(cardId)) {
    return NextResponse.json({ error: "Référence invalide" }, { status: 400 });
  }

  try {
    const response = await fetch("https://api.tcgdex.net/v2/en/cards/" + encodeURIComponent(cardId), {
      signal: AbortSignal.timeout(7000), next: { revalidate: 86400 },
    });
    if (response.status === 404) return NextResponse.json({ image: null });
    if (!response.ok || Number(response.headers.get("content-length") ?? 0) > 2_000_000) throw new Error();
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > 2_000_000) throw new Error();
    const card = JSON.parse(body);
    if (typeof card?.id !== "string" || card.id.toLowerCase() !== cardId.toLowerCase()) throw new Error();
    if (typeof card.image !== "string") return NextResponse.json({ image: null });
    const image = new URL(card.image);
    if (image.origin !== "https://assets.tcgdex.net" || image.username || image.password ||
        image.search || image.hash || !/^\/en\/[a-zA-Z0-9_./-]+$/.test(image.pathname)) {
      return NextResponse.json({ image: null });
    }
    return NextResponse.json({ image: image.href }, {
      headers: { "Cache-Control": "public, max-age=300, s-maxage=3600" },
    });
  } catch {
    return NextResponse.json({ error: "Image temporairement indisponible" }, { status: 503 });
  }
}
