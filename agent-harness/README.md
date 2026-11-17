# EDGE × DeepSeek Harness — isolated integration pilot

DeepSeek Harness is an upstream developer-preview agent runtime (https://github.com/deepseek-ai/deepseek-harness). It is **not** bundled, deployed, or granted access to EDGE infrastructure here.

## Architecture

1. EDGE collector and D1 remain the source of truth. No agent can edit immutable market observations.
2. A future DeepSeek Harness plugin calls a *read-only, allowlisted* EDGE data tool. The runtime never receives Cloudflare/GitHub credentials.
3. The agent returns a typed proposal (facts, weak signals, inferences, thesis, catalysts, risks, entry and exit hypotheses).
4. EDGE validates and records the proposal separately from verified observations; promotion and purchasing require explicit human approval.

This pilot implements the **typed boundary and validation** independently of the upstream harness, to avoid relying on unstable plugin APIs. No API key, external model request, order, payment or paid service is used.

## Local verification

`node --test agent-harness/test/*.test.mjs`

## Next integration gate

In a separate sandbox, pin an upstream dsh release/commit, inspect its actual plugin API and safety model, then write a minimal plugin that calls EDGE's read-only interface. Keep it disabled by default until a security and cost review passes.

## Trusted D1 snapshot handoff

A trusted operator can run a read-only SQL query against the isolated D1 database:

```sql
SELECT product_id, price_kind, currency, source_url, observed_at, price_cents
FROM observations
WHERE price_kind = 'AGGREGATE'
ORDER BY observed_at DESC
LIMIT 500;
```

Save Wrangler's JSON response locally as `d1-select.json`. From the EDGE repository, validate and minimize it with:

```sh
node agent-harness/export-d1.mjs < d1-select.json > agent-harness/data/observations.json
node --test agent-harness/test/*.test.mjs
```

Never include Cloudflare credentials in the agent runtime. The empty snapshot shipped with the repository is intentional. Do not commit a real observation export without reviewing the data and provenance. This export step has **not** yet been executed against remote D1.

## Verified milestone — 2026-11-17

GitHub Actions run #217 validated an authenticated **read-only remote D1 query**: 48 observations across 2 product identifiers were consumed by the native Cordis tool. The CI job also generated two evidence-constrained investigation dossiers in its disposable runner. No prices, source URLs, credentials or snapshots were printed. Temporary exports and dossiers were erased after the job.

The native tool package integration and local SQLite/D1 schema fixture also pass independently. This is not yet a complete DeepSeek Harness agent session or model inference; the pilot has not been deployed to the public EDGE app.

Remaining gates: pin the upstream runtime version, review isolation and cost limits, enable an agent profile in a disposable environment, and verify an actual model-generated proposal against the typed human-review boundary. Never authorize purchases from model output alone.
