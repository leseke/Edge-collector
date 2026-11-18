import { gccVariantKey } from "./gcc-variant.mjs";
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
const lanes = [
  { category: "CARTE", search: "Ventes conclues et annonces de cartes Pokémon individuelles vintage et modernes, de séries variées, brutes ou gradées." },
  { category: "BOOSTER", search: "Ventes conclues et annonces de boosters Pokémon scellés, blisters et displays, toutes séries." },
  { category: "COFFRET", search: "Ventes conclues et annonces de coffrets Pokémon scellés, ETB, UPC, collections et éditions spéciales." },
  { category: "SORTIE", search: "Publications officielles Pokémon sur les sorties TCG, annonces de coffrets et extensions, réassorts, réimpressions et retraits." },
] as const;

export function candidateLeads(text: string) {
  const links = new Map<string, "LOT" | "ANNONCE" | "PUBLICATION">();
  for (const id of candidateLots(text)) links.set(itemPrefix + id, "LOT");
  for (const match of text.matchAll(/https:\/\/[^\s<>")\]]+/g)) {
    try {
      const url = new URL(match[0].replace(/[.,;]+$/, ""));
      if (url.username || url.password || url.port) continue;
      const domain = url.hostname;
      const path = url.pathname;
      const leboncoin = /^(?:www\.)?leboncoin\.fr$/.test(domain) && /^\/ad\/[a-z_]+\/\d+\/?$/.test(path);
      const vinted = /^(?:www\.)?vinted\.fr$/.test(domain) && /^\/items\/\d+(?:-[^/]+)?\/?$/.test(path);
      const official = /^(?:www\.|press\.|support\.)?pokemon\.com$/.test(domain) &&
        /^\/(?:fr\/actualites\/|en\/MEDIA-ALERT-|hc\/fr\/articles\/)[^/]/.test(path);
      if (leboncoin || vinted || official) links.set(url.origin + path, official ? "PUBLICATION" : "ANNONCE");
    } catch {
      continue;
    }
    if (links.size >= 8) break;
  }
  return links;
}

export function candidateLots(text: string): string[] {
  const matches = text.matchAll(new RegExp("https://gradedcardcenter\\.com/(?:fr/|en/)?item/(" + lotPattern + ")(?![a-z0-9/-])", "gi"));
  return [...new Set([...matches].map(match => match[1].toLowerCase()))].slice(0, 2);
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
  const key = gccVariantKey(identity, day);
  if (!key) return null;
  return { lotId, key, day, cents, source: itemPrefix + lotId };
}

async function discoverLeads(apiKey: string, request: Fetch) {
  const topics = lanes.map(lane => `[${lane.category}] ${lane.search}`).join("\n");
  const response = await request(endpoint, {
    method: "POST",
    redirect: "error",
    signal: AbortSignal.timeout(30_000),
    headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
    body: JSON.stringify({
      tools: [{ google_search: {} }],
      generationConfig: { maxOutputTokens: 4096, thinkingConfig: { thinkingBudget: 0 } },
      contents: [{ parts: [{ text: "Recherche Google, marché Pokémon accessible depuis la France. Couvre les quatre familles ensemble.\n" + topics +
        "\nRéponds en texte brut, avec exactement les quatre en-têtes entre crochets ci-dessus, chacun seul sur sa ligne." +
        " Sous chaque en-tête, donne jusqu’à huit URL directes récentes, une par ligne, dont deux lots gradedcardcenter.com/item/ au maximum." +
        " Annonces : Leboncoin ou Vinted. Publications : site officiel Pokémon. Si aucun résultat fiable, garde l’en-tête et indique AUCUN. N’invente aucune URL." }] }],
    }),
  });
  if (response.status === 429 || response.status === 402) return null;
  if (!response.ok) throw new Error("discovery_http_error");
  const data = JSON.parse(await readBoundedText(response, 128_000));
  const answer = data.candidates?.[0];
  if (!answer || answer.finishReason !== "STOP" || !Array.isArray(answer.content?.parts) ||
      !answer.groundingMetadata?.webSearchQueries?.length) throw new Error("discovery_response_invalid");
  const text = answer.content.parts.map((part: {text?: string}) => part.text ?? "").join("\n");
  const sections = text.split(/^[ \t]*\[(CARTE|BOOSTER|COFFRET|SORTIE)\][ \t]*\r?$/m);
  const grouped = new Map<string, ReturnType<typeof candidateLeads>>();
  for (let i = 1; i < sections.length; i += 2) {
    if (!grouped.has(sections[i])) grouped.set(sections[i], candidateLeads(sections[i + 1]));
  }
  return grouped;
}

export async function collectPaidSales(env: PaidSaleEnv, scheduledTime: number, request: Fetch = fetch) {
  if (env.GEMINI_FREE_TIER_ENABLED !== "true" || !env.GEMINI_API_KEY) return;
  const day = new Date(scheduledTime).toISOString().slice(0, 10);
  const claim = await env.DB.prepare("INSERT INTO paid_sale_scans (scan_day,status) VALUES (?,'RUNNING') ON CONFLICT(scan_day) DO NOTHING").bind(day).run();
  if (!claim.meta.changes) return;

  let checked = 0, verified = 0, inserted = 0, failures = 0, discovered = 0;
  const seenUrls = new Set<string>();
  try {
    const grouped = await discoverLeads(env.GEMINI_API_KEY, request);
    discovered = grouped?.size ?? 0;
    for (const lane of lanes) {
      for (const [url, kind] of grouped?.get(lane.category) ?? []) {
        if (seenUrls.has(url)) continue;
        seenUrls.add(url);
        await env.DB.prepare("INSERT INTO market_discovery_leads (source_url,category,kind,first_seen_day) VALUES (?,?,?,?) ON CONFLICT(source_url) DO NOTHING")
          .bind(url, lane.category, kind, day).run();
        if (kind !== "LOT") continue;
        const id = url.slice(itemPrefix.length);
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
    }
  } catch {
    failures++;
  }
  const status = discovered === 0 ? "FAILED" :
    discovered < lanes.length || failures > 0 ? "PARTIAL" : verified > 0 ? "OK" : "EMPTY";
  await env.DB.prepare("UPDATE paid_sale_scans SET status=?,checked=?,verified=?,inserted=? WHERE scan_day=?")
    .bind(status, checked, verified, inserted, day).run();
}
