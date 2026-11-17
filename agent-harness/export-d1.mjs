// Transform a trusted, read-only Wrangler D1 SELECT JSON response to a local snapshot.
// No database credentials, network calls or write operations. stdout only.
import { inspectObservations } from "./edge-readonly-tool.mjs";

export function normalizeD1Export(payload) {
  if (!Array.isArray(payload) || payload.length !== 1 || payload[0]?.success !== true || !Array.isArray(payload[0].results)) throw new Error("invalid_d1_export");
  const rows = payload[0].results;
  if (rows.length > 10000) throw new Error("too_many_rows");
  const products = new Set(rows.map(row => row?.product_id));
  for (const id of products) inspectObservations(rows, id);
  return rows.map(row => ({
    product_id: row.product_id,
    price_kind: row.price_kind,
    currency: row.currency,
    source_url: row.source_url,
    observed_at: row.observed_at,
    price_cents: row.price_cents
  }));
}
if (process.argv[1] && import.meta.url === new URL("file://" + process.argv[1]).href) {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  try {
    const data = normalizeD1Export(JSON.parse(Buffer.concat(chunks).toString("utf8")));
    process.stdout.write(JSON.stringify(data, null, 2) + "\n");
  } catch (error) {
    process.stderr.write(String(error.message) + "\n");
    process.exitCode = 1;
  }
}
