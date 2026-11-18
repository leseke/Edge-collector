import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import { readPaidLot } from "../src/paid-sales.ts";
import { readBoundedText } from "../src/bounded.mjs";

const [sitemapPath, reviewedPath, sqlPath] = process.argv.slice(2);
const sitemap = await readFile(sitemapPath, "utf8");
const reviewed = await readFile(reviewedPath, "utf8");
const known = [...reviewed.matchAll(/gccPaidSale\("([0-9a-f-]{36})"/g)].map(match => match[1]);
const indexed = [...sitemap.matchAll(/<loc>https:\/\/gradedcardcenter\.com\/item\/([0-9a-f-]{36})<\/loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})<\/lastmod>/g)];
indexed.sort((a, b) => b[2].localeCompare(a[2]));
const ids = [...new Set([...known, ...indexed.slice(0, 16).map(match => match[1])])].slice(0, 24);
const now = new Date().toISOString();
const sqlLiteral = value => "'" + value.replaceAll("'", "''") + "'";
const rows = [];
let checked = 0, failures = 0;
const httpFailures = {};
let denied = false;
for (let i = 0; i < ids.length && !denied; i += 2) {
  await Promise.all(ids.slice(i, i + 2).map(async id => {
    checked++;
    try {
      const response = await fetch("https://gradedcardcenter.com/item/" + id, {
        redirect: "error", signal: AbortSignal.timeout(8_000),
        headers: { Accept: "text/html", "Accept-Language": "fr" },
      });
      if (!response.ok) {
        httpFailures[response.status] = (httpFailures[response.status] ?? 0) + 1;
        if (response.status === 403 || response.status === 429) denied = true;
        throw new Error("gcc_item_http_error");
      }
      const html = await readBoundedText(response, 1_500_000);
      const sale = readPaidLot(html, id, now.slice(0, 10));
      if (!sale) return;
      const hash = createHash("sha256").update(html).digest("hex");
      rows.push("(" + [
        sqlLiteral("gcc-" + id), sqlLiteral(sale.key), sqlLiteral(sale.day), sale.cents,
        sqlLiteral(sale.source), sqlLiteral(now), sqlLiteral(hash),
      ].join(",") + ")");
    } catch {
      failures++;
    }
  }));
  if (i + 2 < ids.length && !denied) await delay(500);
}
const sql = rows.length ? `INSERT INTO paid_market_sales
(lot_id,variant_key,sold_day,price_cents,source_url,collected_at,payload_sha256)
VALUES ${rows.join(",")} ON CONFLICT(lot_id) DO NOTHING;\n` : "";
await writeFile(sqlPath, sql);
console.log("GCC paid verification:", JSON.stringify({ checked, verified: rows.length, failures, httpFailures, denied }));
