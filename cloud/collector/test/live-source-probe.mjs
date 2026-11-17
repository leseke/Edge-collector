// Explicit read-only live-source probe. No database writes or paid APIs.
// Run: node cloud/collector/test/live-source-probe.mjs
import { parseIndicativePrice } from "../src/parse.mjs";

const targets = [
  ["pokemon_card_base1_4", "https://api.tcgdex.net/v2/fr/cards/base1-4"],
  ["pokemon_card_swsh3_136", "https://api.tcgdex.net/v2/fr/cards/swsh3-136"],
];
let failures = 0;
for (const [id, url] of targets) {
  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      redirect: "error",
      signal: AbortSignal.timeout(7000),
    });
    if (!response.ok) throw new Error("upstream_" + response.status);
    const body = await response.text();
    if (Buffer.byteLength(body, "utf8") > 128000) throw new Error("oversize");
    const result = parseIndicativePrice(body);
    // Never print or treat a source indicative aggregate as a completed sale.
    console.log(JSON.stringify({
      target: id, status: "OK", price_kind: "AGGREGATE",
      has_indicative_price: result.price !== null,
      source_updated_at: result.updated,
    }));
  } catch (error) {
    failures++;
    const reason = error instanceof Error ? error.message : "unknown";
    console.error(JSON.stringify({ target: id, status: "FAILED", reason }));
  }
}
if (failures) process.exitCode = 1;
