# ADR 038 — Replace manual Leboncoin links with protected ingested-offers view

Date: 2026-11-20
Status: draft PR only, no production deployment or real Outlook sync.

## Product change
The existing Radar Pokémon section required the user to paste each
Leboncoin ad URL into a localStorage form. This contradicted EDGE's goal:
autonomous discovery via Outlook saved-search notifications.

- Remove the manual URL entry, localStorage list and ad removal controls
  from `LeboncoinWatchPanel`; rename the shortcut to Surveillance Leboncoin.
- Show a clear non-synthetic source state when no approved private Worker
  feed is configured, and keep the public saved-search shortcuts only as
  optional reference links.
- Add `GET /internal/outlook/offers` to the isolated collector Worker.
  It is disabled unless `OUTLOOK_ROUTES_ENABLED=true` and
  `OUTLOOK_OFFERS_ENABLED=true`, and requires HTTPS, the registered
  origin and a valid Cloudflare Access signed operator identity.
- Query at most the 50 most recent D1 email-derived listing observations
  and render server-side cards for requested price, title, approximate
  freshness, observed date, original listing link, and source provenance.
  No query/cursor/owner key may be supplied by the request.
- Never label email excerpts as completed sales or verified availability.
  No placeholder market prices, fabricated images or observations.
  Price is null if missing and listings are strictly unverified.
- HTML-escape user-controlled text; require canonical Leboncoin listing
  URLs; send `no-store`, no-referrer and restrictive CSP headers.
- The server-rendered Radar exposes a link to this separate private
  view only if `EDGE_OUTLOOK_OFFERS_URL` is a valid exact HTTPS
  `/internal/outlook/offers` URL without credentials or parameters.
  This environment setting is a navigation pointer, NOT authorization.
  The Worker independently verifies Cloudflare Access.

## Important operational boundary
There is NO live connection between the Next.js app and remote D1 yet.
The new view reads D1 only from its Worker at runtime after a separately
approved deployment, Access policy and schema provisioning. Without
those conditions, the Radar continues to show an honest unconnected
state. This PR does not deploy, activate flags, configure Entra,
migrate remote D1, merge to main, or read actual mailbox data.

## Test strategy
Offline Node tests cover endpoint opt-in, identity rejection, absence
of unauthorized D1 access, safe link rendering, escaping/URL validation,
generic provider failures and no fake observations. The Cloudflare
build validates the Worker; Next.js compile validates Radar integration.
