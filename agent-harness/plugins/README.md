# EDGE DeepSeek Harness tool plugin

`edge-market-tool.ts` follows the official DeepSeek Harness Cordis tool tutorial (`docs/cordis-tutorial/07-into-the-harness.md`). It registers `edge_market_snapshot` through `ctx.tools.register(defineTool(...))`.

The plugin reads only the fixed `../data/observations.json` file (initially `[]`). It does not connect to Cloudflare, fetch URLs, accept filesystem paths from the model, write records, invoke shell commands or authorize purchases.

**Important:** The bundled snapshot is EMPTY, not live. No real observation or successful upstream runtime execution is claimed. Populate the snapshot from a verified read-only D1 export *in a separate trusted process*, then run an isolated dsh profile with no credentials. Never grant this preview runtime access to the EDGE production database or secrets.

The plugin requires the actual published dsh packages and profile patch installation, which must be checked against a pinned upstream version. The CLI probe workflow is manually dispatched and intentionally has no repository secrets.
