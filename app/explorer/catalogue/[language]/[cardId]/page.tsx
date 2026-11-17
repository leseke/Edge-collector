import Link from "next/link";
import { readCatalogueQuote } from "../../../../lib/catalogue-price";
import { getTcgMarketSnapshot } from "../../../../lib/market-data";
import { linkCatalogueToMarket } from "../../../../lib/catalogue-market-link";
import { notFound } from "next/navigation";
import { AssetImage } from "../../../../components/AssetImage";
import "../../../../dashboard.css";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Card = { pricing?: unknown; id?: unknown; name?: unknown; localId?: unknown; image?: unknown; rarity?: unknown; category?: unknown; illustrator?: unknown; hp?: unknown; types?: unknown; set?: { name?: unknown; id?: unknown; releaseDate?: unknown } };

const sourceDate = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" });

function imageUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net" || url.search || url.hash || !/^\/(fr|en|ja)\/[a-zA-Z0-9_./-]+$/.test(url.pathname)) return null;
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
  if (!["fr", "en", "ja"].includes(language) || !/^(?=.{2,50}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*$/.test(cardId)) notFound();
  const sourceUrl = "https://api.tcgdex.net/v2/" + language + "/cards/" + encodeURIComponent(cardId);
  let card: Card | null = null;
  try {
    const response = await fetch(sourceUrl, {
      signal: AbortSignal.timeout(7000), next: { revalidate: 3600 }
    });
    if (!response.ok || Number(response.headers.get("content-length") ?? 0) > 2000000) throw new Error("unavailable");
    const body = await response.text();
    if (new TextEncoder().encode(body).byteLength > 2000000) throw new Error("oversized");
    const value: unknown = JSON.parse(body);
    if (value && typeof value === "object" && !Array.isArray(value)) card = value as Card;
  } catch { /* A catalogue outage is not a missing market observation. */ }
  const field = (value: unknown): string => typeof value === "string" && value.trim() ? value : "Non renseigné";
  const back = "/explorer" + (typeof q === "string" && q.length <= 60 ? "?catalogue=" + encodeURIComponent(q) + "&lang=" + language : "");
  if (!card || card.id !== cardId || typeof card.name !== "string") return <main className="native-dashboard edge-product-detail"><Link href={back}>← Retour au catalogue</Link><h1>Fiche temporairement indisponible</h1><p>Réessaie plus tard. Aucune donnée de marché n'a été inventée.</p></main>;
  const snapshot = await getTcgMarketSnapshot();
  const indicativePrice = readCatalogueQuote(card.pricing);
  const marketLink = linkCatalogueToMarket(cardId, language, snapshot.cards);
  return <main className="native-dashboard edge-product-detail">
    <Link href={back} className="edge-product-back">← Retour au catalogue</Link>
    <p className="native-eyebrow">EDGE / CATALOGUE EXTERNE · TCGDEX</p>
    <div className="edge-product-hero">
      <div className="edge-product-visual"><AssetImage src={imageUrl(card.image)} name={card.name} catalogueId={cardId} catalogueLanguage={language}/></div>
      <div className="edge-product-overview">
        <span className="edge-product-kicker">CARTE RÉFÉRENCÉE · SUIVI EDGE NON ÉTABLI</span>
        <h1>{card.name}</h1>
        <p>{typeof card.set?.name === "string" ? card.set.name : "Extension non renseignée"} · #{typeof card.localId === "string" ? card.localId : "?"} · {language.toUpperCase()}</p>
        <div className="edge-product-primary">
          <span>Indication de marché{indicativePrice ? ` · ${indicativePrice.provider} via TCGdex` : ""}</span>
          {indicativePrice ? (
            <>
              <strong>{new Intl.NumberFormat("fr-FR", { style: "currency", currency: indicativePrice.currency }).format(indicativePrice.low)}</strong>
              <small>
                Prix bas indicatif{indicativePrice.variant ? ` · ${indicativePrice.variant}` : ""} · <a href={sourceUrl}>Source mise à jour le {sourceDate.format(new Date(indicativePrice.updatedAt))}</a>
                {indicativePrice.stale ? " · Donnée de plus de 48 h" : ""}
              </small>
              <small>Vente conclue, langue, édition et état de l’exemplaire non établis par cet indicateur.</small>
            </>
          ) : <strong>Indication de prix indisponible</strong>}
        </div>
      </div>
    </div>
    <section className="edge-catalogue-facts" aria-label="Caractéristiques de la carte">
      <div className="edge-catalogue-facts-heading"><span>IDENTITÉ DU PRODUIT</span><h2>Caractéristiques vérifiables</h2><p>Informations descriptives transmises par TCGdex, sans estimation financière.</p></div>
      <dl className="edge-catalogue-facts-grid">
        <div><dt>Extension</dt><dd>{field(card.set?.name)}</dd></div>
        <div><dt>Numéro</dt><dd>{field(card.localId)}</dd></div>
        <div><dt>Langue</dt><dd>{language.toUpperCase()}</dd></div>
        <div><dt>Rareté</dt><dd>{field(card.rarity)}</dd></div>
        <div><dt>Catégorie</dt><dd>{field(card.category)}</dd></div>
        <div><dt>Illustrateur</dt><dd>{field(card.illustrator)}</dd></div>
        <div><dt>PV</dt><dd>{typeof card.hp === "number" && Number.isFinite(card.hp) ? card.hp : "Non renseigné"}</dd></div>
        <div><dt>Type</dt><dd>{Array.isArray(card.types) ? card.types.filter((type): type is string => typeof type === "string").slice(0, 3).join(", ") || "Non renseigné" : "Non renseigné"}</dd></div>
      </dl>
    </section>
    <section className="edge-catalogue-intelligence" aria-label="Investigation EDGE">
      <span className="edge-product-kicker">INTELLIGENCE EDGE · À CONNECTER</span>
      <h2>Du catalogue à l'investigation</h2>
      <p>Prix réalisés, liquidité, catalyseurs, risques et analyse IA ne sont pas disponibles pour cette fiche. Aucun signal BUY ou STRONG BUY n'est généré sans dossier associé et données traçables.</p>
      <Link href={back}>Revenir à l'exploration</Link>
    </section>
    <section className="edge-product-panel">
      <h2>Provenance et statut</h2>
      <p>Source TCGdex · Identifiant {cardId} · Langue {language.toUpperCase()}</p>
      {marketLink.status === "NO_MATCH" ? (
        <p>Aucun dossier EDGE ni correspondance avec les produits suivis n'est établi pour cette fiche.</p>
      ) : (
        <>
          <p>Correspondance à vérifier · {marketLink.productId}. Pour ce relevé de suivi, aucun prix n’est attribué automatiquement.</p>
          <p>Type de relevé · {marketLink.card.priceKind} · {marketLink.card.source} · {marketLink.card.observedAt}</p>
          <h3>Variante du relevé marché</h3>
          <dl>
            {([
              ["Langue", marketLink.variant.language],
              ["Édition", marketLink.variant.edition],
              ["État", marketLink.variant.condition],
              ["Gradeur", marketLink.variant.grading],
              ["Note", marketLink.variant.grade],
            ] as const).map(([label, evidence]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{evidence.status === "VERIFIED" ? <a href={evidence.source}>{evidence.value}</a> : "Non vérifié"}</dd>
              </div>
            ))}
          </dl>
          <p>Aucun prix ni conseil d’achat n’est déduit de cette correspondance.</p>
          <Link href={`/explorer/${encodeURIComponent(marketLink.productId)}`}>Consulter le relevé EDGE et ses limites</Link>
        </>
      )}
    </section>
  </main>;
}
