# ADR 034 — Sender allowlist before Outlook alerts become price evidence

Date: 2026-11-20
Status: development only; no Microsoft/Cloudflare live connection.

## Threat
The Outlook parser correctly identifies saved-search subject lines and
Leboncoin listing links, but an arbitrary incoming email can forge an
identical subject and link body. Prior to this change, Graph Delta did
not check the sender before writing immutable observations. A forged
message could therefore create false asking-price evidence in EDGE.

## Decision
- Graph Delta now explicitly selects both `from` and `sender`.
- The trusted scheduled/diagnostic collection runner **requires**
  `OUTLOOK_ALLOWED_SENDER_DOMAINS` from private environment
  configuration. If absent/invalid, the collector rejects that run.
- The filter validates exact lowercase domain matches after the @ in
  Graph `from.emailAddress.address`; no suffix/wildcard matches.
  If Graph provides a distinct `sender.emailAddress.address`, this
  must also match the allowlist. Missing/invalid sender metadata fails
  closed. No domain from request parameters, email subject or ad body
  is permitted.
- Rejected messages do not become immutable listing records. They still
  contribute to the Graph page's scanned count, and the Delta checkpoint
  may advance, because they are explicitly outside the approved intake
  policy. This is a conscious operational trade-off; changing the list
  later does NOT automatically backfill previously rejected messages.
- The activation diagnostic checks that the allowlist is configured.
  No email addresses or raw messages are stored in the observation ledger
  for this sender verification.

## Operator verification
The actual sender domain for the target Leboncoin notification MUST be
verified against Graph message metadata before configuring this variable.
We intentionally do not assert a guessed Leboncoin sending domain.
Use a comma-separated list of exact domains without scheme or wildcard,
kept as deployment-side configuration. Reconcile list changes with
checkpoint reset/backfill policy before changing production.

## Limits
A permitted From/Sender domain is necessary but not a complete proof
of message authenticity: delivery-level SPF, DKIM and DMARC results are
not verified by this code, and a compromised approved sender remains a
risk. Price and availability are still `LISTING`/`UNVERIFIED`/
`EMAIL_EXCERPT`, never realized sales or verified current stock.
No live Graph, cloud D1 or operator account was accessed.

## Verification
Offline tests cover approved sender, disallowed domain, lookalike suffix,
different delegated sender, missing metadata and an integrated runner
replay using an explicit synthetic allowlist. Cloudflare and Outlook CI
results are verified on the PR separately.
