import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { GccListingKind } from "../lib/gcc-active-listings";

type Coverage = { observed: number; announced: number | null; checked_at: string; last_complete: string | null };
const number = new Intl.NumberFormat("fr-FR");
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });

export async function GccCoverage({ kind }: { kind: GccListingKind }) {
  let row: Coverage | null = null;
  try {
    const { env } = await getCloudflareContext({ async: true });
    const db = (env as { SALES_DB?: { prepare(sql: string): { bind(kind: string): { first(): Promise<Coverage | null> } } } }).SALES_DB;
    row = await db?.prepare("SELECT observed,announced,checked_at,last_complete FROM gcc_coverage WHERE kind=? AND checked_at IS NOT NULL")
      .bind(kind).first() ?? null;
  } catch { /* Coverage can be unavailable independently of the listings. */ }
  if (!row) return <p className="radar-sales-description">Couverture GCC inconnue pour cette rubrique.</p>;
  return <p className="radar-sales-description">Toutes séries · {number.format(row.observed)} lots uniques relevés
    {row.announced !== null && <> · {number.format(row.announced)} annoncés au départ</>}
    {" · Dernier relevé le "}{date.format(new Date(row.checked_at))}.
    {" "}{row.last_complete ? "Dernier parcours complet le " + date.format(new Date(row.last_complete)) + "." : "Aucun parcours complet confirmé."}</p>;
}
