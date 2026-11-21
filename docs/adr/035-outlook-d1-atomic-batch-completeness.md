# ADR 035 — Atomic completeness assertion for immutable Outlook D1 batches

Date: 2026-11-20
Status: development branch only; not deployed to remote D1.

## Failure mode
Earlier the Outlook writer saved one immutable alert-message row followed by
a set of immutable listing rows inside a D1 batch, but checked only the
message insert's affected-row count. If the D1 lease was valid during the
message INSERT and expired or was replaced before a later listing INSERT,
a guarded listing insert could yield zero rows without throwing. The
message INSERT could commit; the collection would then save the Graph
Delta checkpoint, and a replay would skip the existing immutable message,
silently losing that listing forever.

## Decision
Keep all rows for one email in the same D1 atomic batch. Append a final
*SQL-level assertion* that checks both (1) the expected immutable message
exists with this batch's ingestion timestamp and (2) the number of
immutable listing rows for the message exactly matches the number of
validated listing IDs parsed from the email.

If either condition fails, the final INSERT deliberately attempts a
CHECK-invalid alert row (`advertised_count=-1`). SQLite raises a constraint
error, causing the whole D1 batch transaction to roll back; the Graph
cursor cannot advance because the ingestion operation rejects. On
success, the assertion inserts nothing. The writer verifies the D1
result shape and only counts the actual message and listing statements;
the assertion result never becomes a listing observation.

Existing immutable rows are not modified, and no automated rescan
or checkpoint reset is performed.

## Verification
- A new Python SQLite regression uses the actual migrations 003 and 006,
  with foreign keys enabled, and checks that complete batches commit.
- A second test replaces the lease after one listing insert but before
  the second: the final integrity assertion fails, and BOTH the message
  and earlier listing are rolled back.
- A third test confirms rollback of an otherwise-valid lease batch
  where one listing was not inserted.
- Node D1 mocks, Graph Delta sync and the encrypted full-runner fixture
  now model the conditional assertion's zero-change success result.
- Outlook CI must pass alongside the existing local Wrangler D1 tests.

## Boundaries
This closes the missing-listing-after-message case for newly processed
batches on Cloudflare D1's documented atomic batch implementation; it
does not repair incomplete rows written by older, already deployed
versions (none of this draft integration was deployed), and it does not
prove any real Leboncoin listing is currently available. Rejected Graph
pages retain their existing checkpoint if the DB transaction fails.

No Microsoft mailbox was accessed, no remote migration/deployment was
performed, and `main` remains unchanged.
