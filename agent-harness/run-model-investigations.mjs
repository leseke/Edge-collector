// Explicitly opt-in operator runner; never enabled by CI or the public app.
// Reads a private D1 SELECT export and emits only counts/statuses (no raw model text).
import { readFile } from "node:fs/promises";
import { createDeepSeekAdapter } from "./deepseek-adapter.mjs";
import { runInvestigations } from "./investigation-pipeline.mjs";

export async function main({ argv = process.argv, env = process.env, log = console.log } = {}) {
  if (env.EDGE_ENABLE_PAID_MODEL !== "YES") throw new Error("paid_model_not_enabled");
  if (env.EDGE_ALLOW_MODEL_DATA_TRANSFER !== "YES") throw new Error("model_data_transfer_not_authorized");
  if (!env.DEEPSEEK_API_KEY) throw new Error("model_key_missing");
  const path = argv[2];
  if (!path) throw new Error("missing_private_export");
  const maxCalls = Number(env.EDGE_MAX_MODEL_CALLS ?? "1");
  if (!Number.isSafeInteger(maxCalls) || maxCalls < 1 || maxCalls > 5) throw new Error("invalid_model_call_budget");
  const cursor = Number(env.EDGE_MODEL_CURSOR ?? "0");
  if (!Number.isSafeInteger(cursor) || cursor < 0) throw new Error("invalid_cursor");
  const raw = await readFile(path,"utf8");
  if (Buffer.byteLength(raw,"utf8") > 2_000_000) throw new Error("export_too_large");
  const payload = JSON.parse(raw);
  const generate = createDeepSeekAdapter({ enabled: true, apiKey: env.DEEPSEEK_API_KEY, maxTokens: 800, timeoutMs: 12000 });
  let calls = 0;
  const budgetedGenerate = async brief => {
    if (calls >= maxCalls) throw new Error("model_call_budget_exhausted");
    calls++;
    return generate(brief);
  };
  const result = await runInvestigations(payload, budgetedGenerate, {cursor, maxProducts:maxCalls});
  const counts = {};
  for (const entry of result.results) counts[entry.status] = (counts[entry.status] ?? 0) + 1;
  log(JSON.stringify({modelCallsAttempted:calls,processedProducts:result.processedProducts,remainingProducts:result.remainingProducts,nextCursor:result.nextCursor,statusCounts:counts,purchaseAuthorized:false}));
  return {calls,counts};
}

if (process.argv[1] && import.meta.url === new URL("file://" + process.argv[1]).href) {
  main().catch(error => {
    const allowed = new Set(["paid_model_not_enabled","model_data_transfer_not_authorized","model_key_missing","missing_private_export","invalid_model_call_budget","invalid_cursor","export_too_large"]);
    console.error(allowed.has(error?.message) ? error.message : "model_runner_failed");
    process.exitCode = 1;
  });
}
