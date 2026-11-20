# ADR 040 — Leboncoin first-vs-latest asking-price snapshots

Date: 2026-11-20
Status: feature branch only, without remote D1 deployment.

## Product problem
A listing seen multiple times in different Outlook saved-search
notifications should not become duplicate product cards. But collapsing
the observations entirely also discards useful market-reaction evidence:
the initially requested price versus the latest observed requested price.
Neither observation demonstrates that a sale happened.

## Decision
The private, Cloudflare Access-protected offers view uses a read-only
SQLite window query over immutable `lbc_listing_observations` rows:
- `ROW_NUMBER() ... ORDER BY observed_at DESC, message_id DESC` chooses
  the newest email observation for each stable Leboncoin listing ID;
- `COUNT(*) OVER (PARTITION BY listing_id)` preserves the number of email
  observations of that ID;
- `MIN(observed_at) OVER ...` records the first observed email timestamp;
- `FIRST_VALUE(price_cents) OVER (... ORDER BY observed_at ASC,
  message_id ASC)` records the earliest email asking price.

The card shows first price, latest price and their signed EUR
difference only when there are at least two observations and both
values are valid. This is an **asking-price change between email
snippets**, not completed-sales appreciation, profitability or an
independent real-time listing check.

The query remains restricted to the 50 most recently observed distinct
listings, read-only, with no public URL query parameters, no unverified
user input to SQL and no modifications to the append-only ledger.

## Real-source shape verification
Read-only inspection using the separately connected Outlook mailbox
confirmed that twelve saved-search emails dated 19–20 November 2026
included five direct listing links each: 60 total mentions but 57
distinct IDs. Their advertised totals were much greater than
extracted linked snippets. The HTML-converted email format includes
line-wrapped links and tracking suffixes. A synthetic five-listing
unit fixture reproduces that structure without publishing any raw
mailbox content, private search IDs, email headers or credentials.

## Tests
- Offline Node parser test: five linked snippets are extracted from
  an advertised 1,286-result email, prices/locations retained, links
  canonicalized, all marked unverified LISTING evidence.
- Private offers endpoint test: most recent card shows initially
  reported asking price, delta and first observation timestamp.
- SQLite regression using actual D1 migration 003: duplicate listing
  observations yield one card, latest value, first value, first
  timestamp and count, including distinct-ID and empty-ledger cases.
- GitHub Outlook tests and complete Cloudflare build are checked per
  commit; passing offline tests do NOT prove independent Microsoft
  consent or live D1 connectivity.

## Remaining deployment boundary
No Microsoft Entra authorization has been reused from the ChatGPT
connector. Cloudflare Access, remote D1 migrations, independent
EDGE OAuth consent and the scheduled collector remain inactive.
These changes are part of a draft PR and do not touch main.
