# ADR 039 — Outlook Leboncoin source discovery and distinct offer coverage

Date: 2026-11-20
Status: observational evidence, non-production; no user mail persisted in git.

## Read-only source inspection
An already user-connected Outlook connector returned 12 real Leboncoin
saved-search alerts received on 19–20 November 2026. Their message
subjects were recognized by the existing alert parser, and the
connector's `sender.emailAddress.address` metadata consistently showed
`alerte@recherche.leboncoin.fr`. This supports candidate operator
configuration `OUTLOOK_ALLOWED_SENDER_DOMAINS=recherche.leboncoin.fr`.

**Do not treat this as automatic approval:** the connector's search
representation did not expose a separate `from` property. The dedicated
EDGE Microsoft Graph Delta call must independently verify its `from`
and `sender` fields on first approved consent; no impersonation,
SPF/DKIM/DMARC or actual current listing availability has been proven.

The twelve emails contained 60 direct `/vi/{id}.htm` ad-link
occurrences, representing 57 unique listing IDs. Three ad-link
occurrences repeated across different saved-search alerts. Each email
exposed 5 linked listings, while subject lines claimed a much larger
number of new search results (e.g., 1,286). A notification's advertised
count must NEVER be presented as 1,286 individual importable listing rows
without independent source retrieval. Personal mailbox identifiers,
message body text and raw messages are not committed.

## Product/SQL implementation
The private authenticated offers route now uses SQLite `ROW_NUMBER()
OVER (PARTITION BY listing_id ORDER BY observed_at DESC,message_id DESC)`
to show the newest observation of each unique listing ID, with
`COUNT(*) OVER (PARTITION BY listing_id)` retaining its historical
repeat-appearance signal. The D1 view displays the last email's
`extracted_count` separately from its `advertised_count`, and labels
the values as an unverified asking-price email excerpt rather than
completed sales.

This preserves original append-only D1 history, not overwrites.

## Verification
Offline Node tests check source labels, view status, deduplicated query,
and truthful email coverage. Actual SQLite tests apply migration 003,
seed synthetic repeated listings, and verify one card per listing ID,
repeat-count 2, latest asking-price snapshot, distinct cards and empty
state. No remote D1 changes or automatic mailbox import performed.

## Follow-up
After independent Microsoft Entra consent and approved Cloudflare
deployment, compare the real Graph message `from` and `sender` and
explicitly configure trusted sender domains; audit first imports,
then schedule collection. The earlier Outlook connector grant cannot
be passed to the separate EDGE app.
