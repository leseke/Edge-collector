import Link from "next/link";
import { notFound } from "next/navigation";
import { AssetImage } from "../../../../components/AssetImage";
import "../../../../dashboard.css";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Card = { id?: unknown; name?: unknown; localId?: unknown; image?: unknown; set?: { name?: unknown } };
function imageUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net" || url.search || url.hash || !/^\/(fr|en|ja)\/[a-zA-Z0-9_/-]+$/.test(url.pathname)) return null;
    const path = url.pathname.replace(/\/$/, "");
    return /\/(high|low)\.(webp|png|jpg)$/.test(path) ? url.href : url.origin + path + "/high.webp";
  } catch { return null; }
}
export default async function CatalogueCardPage({ params, searchParams }: {
  params: Promise<{ language: string; cardId: string }>;
  searchParams: Promise<{ q?: string }>;
}) {
  const { language, cardId } = await params;
  const { q } = await searchParams;
  if (!["fr", "en", "ja"].includes(language) || !/^[a-zA-Z0-9-]{2,50}$/.test(cardId)) notFound();
  let card: Card | null = null;
  try {
    const response = await fetch("https://api.tcgdex.net/v2/" + language + "/cards/" + encodeURIComponent(cardId), {
      signal: AbortSignal.timeout(7000), next: { revalidate: 3600 }
    });
    if (!response.ok || Number(response.headers.get("content-length") ?? 0) > 2000000) throw new Error("unavailable");
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > 2000000) throw new Error("oversized");
    const value: unknown = JSON.parse(body);
    if (value && typeof value === "object" && !Array.isArray(value)) card = value as Card;
  } catch { /* A catalogue outage is not a missing market observation. */ }
  const back = "/explorer" + (typeof q === "string" && q.length <= 60 ? "?catalogue=" + encodeURIComponent(q) + "&lang=" + language : "");
  if (!card || card.id !== cardId || typeof card.name !== "string") return <main className="native-dashboard edge-product-detail"><Link href={back}>← Retour au catalogue</Link><h1>Fiche temporairement indisponible</h1><p>Réessaie plus tard. Aucune donnée de marché n'a été inventée.</p></main>;
  return <main className="native-dashboard edge-product-detail">
    <Link href={back} className="edge-product-back">← Retour au catalogue</Link>
    <p className="native-eyebrow">EDGE / CATALOGUE EXTERNE · TCGDEX</p>
    <div className="edge-product-hero">
      <div className="edge-product-visual"><AssetImage src={imageUrl(card.image)} name={card.name}/></div>
      <div className="edge-product-overview">
        <span className="edge-product-kicker">CARTE RÉFÉRENCÉE · NON SUIVIE PAR EDGE</span>
        <h1>{card.name}</h1>
        <p>{typeof card.set?.name === "string" ? card.set.name : "Extension non renseignée"} · #{typeof card.localId === "string" ? card.localId : "?"} · {language.toUpperCase()}</p>
        <div className="edge-product-primary"><span>Prix de marché</span><strong>Non collecté</strong><small>TCGdex fournit ici une identité de catalogue, pas une observation de prix ni une opportunité validée.</small></div>
      </div>
    </div>
    <section className="edge-product-panel"><h2>Provenance et statut</h2><p>Source : TCGdex · Identifiant : {cardId} · Langue : {language.toUpperCase()}</p><p>Aucun dossier EDGE ni correspondance avec les produits suivis n'est établi pour cette fiche.</p></section>
  </main>;
}
