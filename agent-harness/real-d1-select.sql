-- Read-only, bounded market export. Never run writes in this workflow.
SELECT product_id, price_kind, currency, source_url, observed_at, price_cents
FROM observations
WHERE price_kind = 'AGGREGATE' AND currency = 'EUR'
ORDER BY observed_at DESC, observation_id DESC
LIMIT 500;
