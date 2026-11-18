import type { SaleVariant } from "./radar-paid-sales";

const catalog: Record<string, string> = {
  "swsh7-215": "carte:2021:evolution-celeste:215/203:noctali-vmax",
  "swsh8-157": "carte:2021:poing-de-fusion:157/264:ectoplasma-vmax",
};
const languages: Record<string, string> = {
  francais: "fr", anglais: "en", japonais: "ja", allemand: "de", espagnol: "es", italien: "it",
};
const normalize = (value: string) => value.normalize("NFD").replace(/\p{Diacritic}/gu, "").trim().toLowerCase();
const keyPart = (value: string) => normalize(value).replace(/[^a-z0-9./]+/g, "-");

export function listingCardKey(title: string, subtitle: string, series: string | null) {
  const fields = normalize(subtitle).split(/\s*•\s*/);
  const [language, year, set, edition, number] = fields;
  const graded = normalize(title).match(/^(pca|psa|ccc|cgc|bgs|sgc)\s+(10|[1-9](?:\.5)?)\s+([a-z0-9][a-z0-9 '’.-]+)$/);
  if (fields.length !== 5 || !series || !graded || !languages[language] || set !== normalize(series) ||
      !/^\d{4}$/.test(year) || !/^(unlimited|first edition)$/.test(edition) || !/^#[a-z0-9]+\/[a-z0-9]+$/.test(number)) return null;
  return ["carte", year, keyPart(set), number.slice(1), keyPart(graded[3]), languages[language], keyPart(edition), graded[1], graded[2]].join(":");
}

function canonical(key: string) {
  const [first, ...rest] = key.split(":");
  return catalog[first] ? [catalog[first], ...rest].join(":") : key;
}

export function comparableSales(variants: SaleVariant[], key: string | null, lotId: string, today: string) {
  const known = variants.find(v => v.paidSales.some(s => s.id === lotId));
  const target = known?.key ?? key;
  if (!target) return null;
  const exactKey = canonical(target);
  const family = exactKey.startsWith("carte:") ? exactKey.split(":").slice(0, 5).join(":") + ":" : null;
  type Row = SaleVariant["paidSales"][number] & { variant: string };
  const exact = new Map<string, Row>();
  const related = new Map<string, Row>();
  for (const variant of variants) {
    const candidate = canonical(variant.key);
    const rows = candidate === exactKey ? exact : family && candidate.startsWith(family) ? related : null;
    if (!rows) continue;
    for (const sale of variant.paidSales) {
      if (sale.id === lotId || sale.day > today || !Number.isSafeInteger(sale.cents) || sale.cents <= 0) continue;
      rows.set(sale.id, { ...sale, variant: variant.variant });
    }
  }
  for (const id of exact.keys()) related.delete(id);
  const newest = (rows: Map<string, Row>) => [...rows.values()].sort((a, b) => b.day.localeCompare(a.day) || a.id.localeCompare(b.id));
  const prices = [...exact.values()].map(row => row.cents).sort((a, b) => a - b);
  const mid = Math.floor(prices.length / 2);
  const median = prices.length >= 2 ? (prices[mid] + prices[Math.floor((prices.length - 1) / 2)]) / 2 : null;
  return { exact: newest(exact), related: newest(related), median };
}
