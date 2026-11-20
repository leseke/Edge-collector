# ADR 036 — Fail-closed replay of legacy incomplete Outlook alert records

Date: 2026-11-20
Status: development only, no remote D1 or Outlook access.

## Issue
A D1 alert message can preexist its full listing ledger (for example,
from a legacy batch, compromised import or manually corrupted test row).
The previous writer performed `SELECT 1 FROM lbc_alert_messages` and
treated the existence of its message ID as a complete duplicate. A
subsequent Graph Delta run could therefore advance its checkpoint while
silently ignoring missing immutable listing records. ADR 035 prevents
NEW incomplete batches but does not validate already-existing emails.

## Resolution
Before skipping an existing email, query the immutable ledger for:
1. the message's stored `extracted_count`;
2. the actual listing row count for the message; and
3. the number of rows whose listing IDs match the *current parsed email*
   (using bound SQL placeholders, never string interpolation of IDs).

The counts must agree, including the expected number from the current
validated alert. Zero listings are valid only when all counts are zero.
On any missing, incomplete, stale, replaced, or inconsistent record,
the writer throws `outlook_existing_message_incomplete_or_changed`.
Graph Delta therefore **does not advance its cursor**. No update or
delete of immutable observations is permitted.

The integrity query verifies IDs and counts, not the full equality of
titles, timestamps or prices. Such field-level snapshot differences
would require an explicit schema-evolution/reconciliation policy.

## Tests
- Node tests verify complete replay, a partially archived message, and
  equal-count but swapped listing IDs.
- Graph Delta test asserts an incomplete archived message blocks its
  checkpoint, and a batch writer is never invoked.
- Real SQLite regression applies migration 003 and checks that the
  parameterized integrity query distinguishes missing records, exact
  matches, and same-count mismatched listing IDs.
- Existing OAuth→Graph→D1 runner replay tests remain in CI.
- No remote account, credential or real announcement used.

## Operations
Existing bad immutable records must be investigated and recovered with
a separately approved append-only reconciliation/backfill procedure.
They must not be silently overwritten, deleted or treated as legitimate
price observations. No production change, merged PR, cron or remote D1
migration occurred in this implementation.
