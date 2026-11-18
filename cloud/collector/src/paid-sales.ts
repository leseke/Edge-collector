import { readBoundedText } from "./bounded.mjs";

type Fetch = typeof fetch;
export type PaidSaleEnv = {
  DB: D1Database;
  GEMINI_API_KEY?: string;
  GEMINI_FREE_TIER_ENABLED?: string;
};

const endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";
const lotPattern = "[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}";
const itemPrefix = "https://gradedcardcenter.com/item/";
const supportedCards = [
  { id: "swsh7-215", name: "Noctali", set: "Evolution Celeste", number: "215/203", releasedOn: "2021-08-27", grades: ["PCA 9", "PCA 9.5", "PSA 10"] },
  { id: "swsh8-157", name: "Ectoplasma", set: "Poing de Fusion", number: "157/264", releasedOn: "2021-11-12", grades: ["PCA 9.5", "PSA 10"] },
] as const;

export function candidateLots(text: string): string[] {
  const matches = text.matchAll(new RegExp("https://gradedcardcenter\\.com/(?:fr/|en/)?item/(" + lotPattern + ")(?![a-z0-9/-])", "gi"));
  return [...new Set([...matches].map(match => match[1].toLowerCase()))].slice(0, 8);
}

export function readPaidLot(html: string, lotId: string, scanDay: string) {
  if (!new RegExp("^" + lotPattern + "$").test(lotId)) return null;
  const text = html
    .replace(/<!--[\s\S]*?-->|<(script|style|template)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&(?:nbsp|#160|#8239);/gi, " ")
    .replace(/&(?:euro|#8364);/gi, "€")
    .replace(/&(?:apos|#39|rsquo|#8217);/gi, "'")
    .normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/\s+/g, " ");
  const soldPage = text.match(/Article vendu\b(.{0,650}?)\bPrix de vente\b\s+([0-9][0-9'’ .]*(?:,\d{2})?)\s*€(.{0,220}?)\b(\d{2})\/(\d{2})\/(\d{4})\s+Statut du paiement\s+Paye\b(?!\s+(?:partiellement|en attente))/i);
  if (!soldPage) return null;
  const [, identity, amount, , dd, mm, yyyy] = soldPage;
  const day = `${yyyy}-${mm}-${dd}`;
  const time = new Date(day + "T00:00:00Z");
  if (!Number.isFinite(+time) || time.toISOString().slice(0, 10) !== day || day > scanDay) return null;
  const [whole, decimals = "00"] = amount.trim().split(",");
  if (!/^\d+$/.test(whole) && !/^\d{1,3}(?:[ '’]\d{3})+$/.test(whole)) return null;
  const cents = Number(whole.replace(/[ '’]/g, "")) * 100 + Number(decimals);
  if (!Number.isSafeInteger(cents) || cents <= 0) return null;
  const metadata = identity.match(/\bPokemon\s*•\s*(?:French|Francais)\s*•\s*2021\s*•\s*([^•]+?)\s*•\s*Unlimited\s*•\s*#(\d+\/\d+)(?![\d/])/i);
  const card = supportedCards.find(x => metadata?.[1].toLowerCase() === x.set.toLowerCase() && metadata[2] === x.number);
  if (!metadata || !card || day < card.releasedOn) return null;
  const title = identity.slice(0, metadata.index).replace(/\s+/g, " ").trim();
  const grade = card.grades.find(value => title.toLowerCase().endsWith((value + " " + card.name + " VMAX").toLowerCase()) &&
    /(?:^|\s)(?:PCA|PSA)\s+\d+(?:\.\d+)?\s+\w+\s+VMAX$/i.test(title));
  if (!grade) return null;
  const [grader, score] = grade.toLowerCase().split(" ");
  return { lotId, key: card.id + ":fr:unlimited:" + grader + ":" + score, day, cents, source: itemPrefix + lotId };
}

export async function collectPaidSales(env: PaidSaleEnv, scheduledTime: number, request: Fetch = fetch) {
  if (env.GEMINI_FREE_TIER_ENABLED !== "true" || !env.GEMINI_API_KEY) return;
  const day = new Date(scheduledTime).toISOString().slice(0, 10);
  const claim = await env.DB.prepare("INSERT INTO paid_sale_scans (scan_day,status) VALUES (?,'RUNNING') ON CONFLICT(scan_day) DO NOTHING").bind(day).run();
  if (!claim.meta.changes) return;

  let checked = 0, verified = 0, inserted = 0, failures = 0;
  let discoveryFailed = false;
  try {
    const response = await request(endpoint, {
      method: "POST",
      redirect: "error",
      signal: AbortSignal.timeout(30_000),
      headers: { "Content-Type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
      body: JSON.stringify({
        tools: [{ google_search: {} }],
        generationConfig: { maxOutputTokens: 2048, thinkingConfig: { thinkingBudget: 0 } },
        contents: [{ parts: [{ text: "Recherche Google. Trouve les liens publics les plus récents gradedcardcenter.com/item/ des lots vendus pour Noctali VMAX 215/203 ou Ectoplasma VMAX 157/264, français Unlimited, grade PCA 9, PCA 9.5 ou PSA 10. Renvoie seulement jusqu’à huit URL directes de lots. N’invente aucune URL." }] }],
      }),
    });
    if (!response.ok) throw new Error("discovery_http_error");
    const data = JSON.parse(await readBoundedText(response, 128_000));
    const answer = data.candidates?.[0];
    if (!answer || answer.finishReason !== "STOP" || !Array.isArray(answer.content?.parts) ||
        !answer.groundingMetadata?.webSearchQueries?.length) throw new Error("discovery_response_invalid");
    const text = answer.content.parts.map((part: {text?: string}) => part.text ?? "").join("\n");
    for (const id of candidateLots(text)) {
      checked++;
      try {
        const page = await request(itemPrefix + id, {
          redirect: "error", signal: AbortSignal.timeout(8000),
          headers: { "Accept-Language": "fr-FR,fr;q=0.9", Accept: "text/html" },
        });
        if (!page.ok || !page.headers.get("content-type")?.includes("text/html")) throw new Error("lot_response_invalid");
        const html = await readBoundedText(page, 1_500_000);
        const sale = readPaidLot(html, id, day);
        if (!sale) continue;
        verified++;
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(html));
        const sha = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
        const written = await env.DB.prepare(`INSERT INTO paid_market_sales
          (lot_id,variant_key,sold_day,price_cents,source_url,collected_at,payload_sha256)
          VALUES (?,?,?,?,?,?,?) ON CONFLICT(lot_id) DO NOTHING`)
          .bind("gcc-" + id, sale.key, sale.day, sale.cents, sale.source, new Date().toISOString(), sha).run();
        inserted += written.meta.changes ?? 0;
      } catch {
        failures++;
      }
    }
  } catch {
    discoveryFailed = true;
  }
  const status = discoveryFailed || (failures > 0 && failures === checked) ? "FAILED" :
    failures > 0 ? "PARTIAL" : verified > 0 ? "OK" : "EMPTY";
  await env.DB.prepare("UPDATE paid_sale_scans SET status=?,checked=?,verified=?,inserted=? WHERE scan_day=?")
    .bind(status, checked, verified, inserted, day).run();
}
