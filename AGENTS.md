# Navigating EDGE with Graphify

Use Graphify for unfamiliar code paths and changes spanning collection, processing, and display. For a known file or an exact field name, open it directly or use `rg`.

Install the tested CLI into an isolated tool environment and build the graph from the repository root:

```sh
uv tool install graphifyy==0.9.112
GRAPHIFY_BACKEND=none graphify extract . --code-only
```

Regenerate after switching branches or changing the code relevant to your question. Keep the graph local and use a short query seeded with a symbol or filename. Start with depth 1 and a budget of roughly 400 tokens:

```sh
GRAPHIFY_QUERY_LOG_DISABLE=1 graphify query 'getTcgMarketSnapshot CardTile' --depth 1 --budget 400
```

Open the returned source locations to verify the path. Use exact source searches for serialized fields and connections across services or snapshots. For example, follow `market_language_verified` across the collector, snapshot reader, and display. Preserve the distinction between the language of a TCGdex card record and the language of the offers underlying a price.
