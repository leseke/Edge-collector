#!/usr/bin/env node
// Read-only Microsoft Graph probe. Requires a Microsoft Graph OAuth access token
// with Mail.Read. Never commit tokens, mail contents, or generated listing output.
import { collectGraphAlerts } from "./leboncoin-email.mjs";
import { writeFile } from "node:fs/promises";
const token = process.env.EDGE_OUTLOOK_GRAPH_ACCESS_TOKEN;
if (!token) {
  console.error("missing_graph_token: set EDGE_OUTLOOK_GRAPH_ACCESS_TOKEN via a secure secret manager");
  process.exitCode = 2;
} else {
  try {
    const maxPages = Number(process.env.EDGE_OUTLOOK_MAX_PAGES || "10");
    const result = await collectGraphAlerts({ token, maxPages });
    const output = process.env.EDGE_OUTLOOK_OUTPUT;
    if (output) {
      await writeFile(output, JSON.stringify(result, null, 2) + "\n", {flag:"wx",mode:0o600});
      console.log(JSON.stringify({status:result.status,scanned:result.scanned,alerts:result.alerts.length,
        unique_listings:result.listings.length,remaining_pages_possible:result.remaining_pages_possible}));
    } else {
      // Default only prints counts to avoid accidental private mailbox disclosure.
      console.log(JSON.stringify({status:result.status,scanned:result.scanned,alerts:result.alerts.length,
        unique_listings:result.listings.length,remaining_pages_possible:result.remaining_pages_possible}));
    }
    if (result.status === "PARTIAL") process.exitCode = 3;
  } catch (error) {
    console.error("outlook_ingestion_failed:", String(error?.message || "unknown").replace(/Bearer\s+[^\s]+/g,"Bearer [REDACTED]"));
    process.exitCode = 1;
  }
}
