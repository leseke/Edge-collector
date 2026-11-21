# ADR 029 — Cancel Microsoft refresh and identity checks when Outlook run lease expires

Date: 2026-11-19
Status: Development branch only; not mounted or deployed.

## Context
Outlook D1 inserts and checkpoints now use lease-fenced SQL. The Graph
Delta reader accepts an AbortSignal, but the OAuth refresh and Graph
/me identity requests previously did not receive it. Thus, a collector
could waste time and external requests after cancellation, although
a later lease-fenced D1 write would fail.

## Change
- `refreshMicrosoftGraphToken` accepts the caller's AbortSignal and
  passes it to the token exchange HTTP request.
- `runWithMicrosoftToken` invokes the existing asynchronous lease
  validity check before credential reads, after reads, after refresh,
  and before credential rotation / running the Graph consumer.
- `verifyMicrosoftMailbox` accepts and forwards the cancellation signal.
- `runOutlookLeboncoinCollection` passes the D1 lease's signal and
  checker through token refresh, Graph identity and Delta fetch.
- Regression tests ensure loss of the lease after token exchange does
  not persist a rotated refresh token or start message collection.

## Limits
AbortSignal is cooperative: it cannot undo a Microsoft token refresh
already accepted by Microsoft and not all custom fetch adapters must
honor cancellation. D1 owner fencing and credential generation CAS
remain essential. Real Microsoft Entra consent and Cloudflare Access
identity configuration are still absent; this ADR does not authorize
production runtime activation or independent credential reuse.

## Verification
Offline deterministic tests run in Outlook and overall Cloudflare CI;
only confirmed job conclusions are evidence. No secret, production
database write, scheduled collection or `main` modification.
