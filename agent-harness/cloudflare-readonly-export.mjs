// Trusted CI-only Cloudflare D1 SELECT exporter. Never give this script to the agent.
// Cloudflare token is read from the environment and never printed or persisted.
import { writeFile } from "node:fs/promises";
const token = process.env.CLOUDFLARE_API_TOKEN;
const destination = process.argv[2];
if (!token || !destination) throw new Error("missing_cloudflare_token_or_destination");
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 20000);
async function cf(path, init = {}) {
  const response = await fetch("https://api.cloudflare.com/client/v4" + path, {
    ...init, signal: controller.signal,
    headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" }
  });
  if (!response.ok) throw new Error("cloudflare_http_" + response.status);
  const payload = await response.json();
  if (payload.success !== true) throw new Error("cloudflare_api_failure");
  return payload.result;
}
try {
  const accounts = await cf("/accounts?per_page=100");
  if (!Array.isArray(accounts) || accounts.length !== 1) throw new Error("ambiguous_cloudflare_account");
  const account = accounts[0].id;
  if (!/^[0-9a-f]{32}$/i.test(account)) throw new Error("invalid_account_id");
  const databases = await cf("/accounts/" + account + "/d1/database?per_page=100");
  const matches = databases.filter(db => db.name === "edge-tcg-history");
  if (matches.length !== 1 || !/^[0-9a-f-]{36}$/i.test(matches[0].uuid)) throw new Error("ambiguous_d1_database");
  const sql = "SELECT product_id, price_kind, currency, source_url, observed_at, price_cents FROM observations WHERE price_kind = 'AGGREGATE' AND currency = 'EUR' ORDER BY observed_at DESC, observation_id DESC LIMIT 500";
  const result = await cf("/accounts/" + account + "/d1/database/" + matches[0].uuid + "/query", { method: "POST", body: JSON.stringify({ sql }) });
  if (!Array.isArray(result) || result.length !== 1 || result[0]?.success !== true || !Array.isArray(result[0]?.results)) throw new Error("invalid_query_response");
  await writeFile(destination, JSON.stringify(result), { mode: 0o600, flag: "wx" });
  console.log("D1 read-only SELECT completed. Response saved in private runner temp file; rows=" + result[0].results.length);
} finally {
  clearTimeout(timeout);
}
