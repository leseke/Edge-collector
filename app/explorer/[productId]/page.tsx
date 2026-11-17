import Link from "next/link";
import { notFound } from "next/navigation";
import { getTcgMarketSnapshot } from "../../lib/market-data";
import { AssetImage } from "../../components/AssetImage";
import "../../dashboard.css";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function price(value: number | null, currency: string): string {
  if (value === null || !Number.isFinite(value)) return "Indisponible";
  try { return new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(value); }
  catch { return "Indisponible"; }
}
function observed(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "Non renseigné" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "Europe/Paris" }).format(d);
}
export default async function ProductPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params;
  if (!/^pokemon_card_[a-zA-Z0-9_-]{1,100}$/.test(productId)) notFound();
  const snapshot = await getTcgMarketSnapshot();
  const card = snapshot.cards.find(item => item.productId === productId);
  if (!card) notFound();
  const investigation = snapshot.reactionCases.find(item => item.productId === productId);
  return <div className="native-dashboard edge-product-detail">
    <Link href="/explorer" className="edge-product-back">← Retour à l'Explorateur</Link>
    <p className="native-eyebrow">EDGE / FICHE PRODUIT</p>
    <div className="edge-product-hero">
      <div className="edge-product-visual"><AssetImage src={card.image} name={card.name}/></div>
      <div className="edge-product-overview">
        <span className="edge-product-kicker">POKÉMON · CARTE · {card.setName}</span>
        <h1>{card.name}</h1>
        <p>Numéro {card.number} · {card.rarity}</p>
        <div className="edge-product-primary"><span>Prix indicatif bas observé</span><strong>{price(card.low, card.currency)}</strong><small>Il ne s'agit pas d'une vente conclue vérifiée.</small></div>
        <div className="edge-product-tags"><span>Langue {card.languageVerified ? "vérifiée" : "non vérifiée"}</span><span>État non vérifié</span><span>Disponibilité {card.availability === "UNKNOWN" ? "inconnue" : card.availability}</span></div>
      </div>
    </div>
    <div className="edge-product-sections">
      <section className="edge-product-panel"><p className="native-eyebrow">01 / DONNÉES DE MARCHÉ</p><h2>Prix & provenance</h2>
        <dl className="edge-product-facts">
          <div><dt>Prix bas indicatif</dt><dd>{price(card.low, card.currency)}</dd></div>
          <div><dt>Moyenne indicative</dt><dd>{price(card.average, card.currency)}</dd></div>
          <div><dt>Tendance indicative</dt><dd>{price(card.trend, card.currency)}</dd></div>
          <div><dt>Source du relevé</dt><dd>{card.source}</dd></div>
          <div><dt>Date d'observation</dt><dd>{observed(card.observedAt)}</dd></div>
          <div><dt>Mise à jour source</dt><dd>{card.sourceUpdatedAt ? observed(card.sourceUpdatedAt) : "Non renseignée"}</dd></div>
          <div><dt>Type de prix</dt><dd>{card.priceKind || "Non renseigné"}</dd></div>
        </dl><p className="edge-product-disclaimer">Ces valeurs ne permettent pas de calculer un rendement prévisionnel fiable. La langue, la variante, l'état et les frais de transaction restent à confirmer.</p>
      </section>
      <section className="edge-product-panel edge-product-ai-panel"><p className="native-eyebrow">02 / EDGE INTELLIGENCE</p><h2>Enquête & analyse IA</h2><p>{investigation ? `Dossier MRI lié : ${investigation.publicationCount} publication(s) référencée(s). Réaction : ${investigation.reactionStatus}. Décision : ${investigation.financialDecision}.` : "Aucun dossier MRI lié à ce produit dans le dernier relevé vérifiable. Cela ne signifie pas que le produit est sans potentiel."}</p><div className="edge-product-ai-status">Agent conversationnel DeepSeek non activé</div><Link href="/mri" className="edge-ai-link">Consulter le Radar →</Link></section>
    </div>
  </div>;
}
