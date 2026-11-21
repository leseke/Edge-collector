# ADR 015 — Outlook Leboncoin saved-search mail ingestion

Status: development prototype (2026-11-19). No production mailbox watcher enabled.

## Context
Outlook Leboncoin saved-search notifications contain a total results count but only a
short subset of clickable ad excerpts. Treating the headline as a set of imported
listings creates fabricated coverage. EDGE needs source provenance, deduplication
and evidence boundaries prior to any investor-facing recommendations.

## Options considered
1. Scrape Leboncoin directly: potentially deeper coverage, but reliability,
   authentication and service terms require separate evaluation.
2. Parse Outlook saved-search emails through Microsoft Graph Mail.Read:
   read-only, user-authorized, already validated as carrying direct listing links;
   incomplete email coverage must remain explicit.
3. Forward mail to a third-party mailbox: unnecessary private data propagation.

## Decision
Choose option 2 as a **read-only, bounded development collector**. Implement
a pure email parser, Graph list-pages adapter, CLI, synthetic contract tests.
Do not treat generic ChatGPT Outlook connection as a transferable OAuth token
for GitHub or Cloudflare. Separate Azure OAuth consent and secure credential
provisioning remain prerequisites for unattended EDGE runs.

### Contract
Input: Graph message with id, subject, receivedDateTime and body.content.
Accepted subject: `<saved search>: <integer> nouveaux résultats`.
Output alert: message_id, received_at, search, advertised_count, extracted_count,
truncated_email, listings.
Output listing: stable `leboncoin:<listing id>`, canonical source_url, title,
price_cents, currency, location, category_hint, observed_at, price_kind=LISTING,
availability=UNVERIFIED, evidence=EMAIL_EXCERPT.
Combined feed deduplicates by ID and remembers matching saved searches.

### Constraints
- No completed-sale or demand inference from a saved-search alert.
- The advertised count is not actual extracted inventory.
- Mail may show truncated titles/images and stale prices; listing must be
  revalidated before actionable recommendations.
- No email user/profile/security mail import. Restrict to known alert subjects.
- Cap Graph fetch pages, validate nextLink origin/path, and avoid writing token
  or personal message bodies to logs.
- CLI defaults to counts only. Explicit output goes to exclusive mode-0600 file,
  ignored by operator's own storage policy; do not commit artifacts.
- No purchases, paid API, deployment, or production D1 writes.

### Follow-up before autonomous launch
1. Dedicated Microsoft Graph Mail.Read OAuth consent for EDGE with renewable
   token storage and least privilege (not ChatGPT's connector token).
2. Durable append-only observations and separate per-message idempotency
   checkpoint in D1. Explicit status/error journaling and incremental sync.
3. Operational scheduler + rate limiting, retries, token rotation, alert
   monitoring, credential audit and privacy/retention decision.
4. Live source cross-check of offer availability/images and source attribution.
5. CI evidence, UX review and explicit deployment approval.

## Reversibility
All changes live on an isolated branch and add new standalone files.
No existing routes, migrations, or production secrets were changed.
