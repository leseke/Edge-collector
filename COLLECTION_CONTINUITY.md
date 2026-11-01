# EDGE — Collection continuity, 2026-11-01

## Evidence

GitHub's scheduled-run history was compared with the workflow definitions at the exact recorded commit SHAs. The successful commercial runs around the observed overnight gap were 41245422467 (created 2026-10-31 21:50:08 UTC) and 41282248988 (created 2026-11-01 06:47:49 UTC). Both used dd1579135cd60e08e6dcef72a13c8c8893f5d16c, whose workflow still scheduled `37 */6 * * *`, not the later three-hour configuration. The preceding job started 21:50:12 and ended 21:51:28 UTC, including successful archival: it was not executing for the whole gap.

Selected public API fields and provenance are retained in research/scheduler_audit_2026-11-01.json. The available records do not prove which nominal cron occurrence produced each delayed run, or the internal reason for a missing/delayed invocation. No historical price, stock or outcome is reconstructed.

GitHub documents that scheduled events can be delayed and that queued jobs may be dropped under high load: https://docs.github.com/en/actions/how-tos/troubleshoot-workflows . Moving the minute alone cannot guarantee timely delivery.

## Implemented mitigation

The existing commercial workflow now wakes hourly at minute 17 UTC. Under the existing serialized writer lock it loads the persistent data branch and verifies latest.json against the archived report's SHA-256, path, schema, timestamp and status.

A scheduled invocation skips external market collection only if the last report is less than three hours old, OK/PARTIAL, and contains at least one valid recent EUR asking-price proof. At the three-hour boundary it collects. Corrupt/missing/future evidence, failed captures and indicative-card-only results cannot suppress a new attempt. Push and explicit manual invocations continue to collect. A skipped invocation writes its reason to the Actions step summary and creates no market snapshot, no forecast outcome and no latest pointer.

This gives hourly opportunities to recover after a delayed invocation while aiming for approximately three hours between successful captures. It remains dependent on GitHub's scheduler; it is not an independent fallback or a punctuality guarantee. Persistent source failures can trigger hourly retries, within the existing per-run source cap. Neither paid access nor messaging is introduced.

Each new report records `collection_trigger` with event, run ID and attempt. The public interface distinguishes schedule, code-change and manual captures. Older archives lacking this metadata are not retroactively labelled autonomous.

## Verification and next evidence

Unit checks cover skip/collect boundaries, failed/inadequate evidence, checksum/path failures, future dates and explicit triggers. The production push verifies the collection path. A future genuine schedule event is required to verify the new hourly gate in production; a push or local test cannot prove scheduler delivery.

Next check: inspect the first genuine scheduled invocations and their guard decisions, then compare the next overnight archive intervals. If multi-hour delivery gaps persist, a separately hosted scheduler would be required; adding another GitHub cron would still share the same dependency.
