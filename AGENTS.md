# EDGE engineering rules

Scope: development branch only. Never modify main, deploy, merge, purchase, or invoke a paid provider without explicit user authorization. Production promotion requires CI output supplied and approved by the user.

Source-of-truth order: SPEC.md (intended scope), docs/CONTRAT.md (implemented and proposed interfaces), docs/adr/ (decisions), STATE.md (verified state). Never represent a proposed interface as implemented.

Before coding: document types, D1 schema, routes, payloads, edge cases and a verifiable done criterion; await user GO. For each implementation step: code and tests, user-run CI evidence, critique, corrections, STATE update. Do not claim success without an execution result.

Facts must carry provenance. Separate FACT / WEAK_SIGNAL / INFERENCE / BET; matching citation metadata does not prove semantic claims. Synthetic fixtures are never market evidence. No model output can authorize a transaction. Keep model credentials out of frontend, logs, and git. External model calls and data transfer require explicit opt-in and cost controls.

Every structural decision requires docs/adr/NNN-title.md with context, two or more options, decision, rationale, consequences and reversibility. Prefer reversible decisions. Preserve historical observations. No framework migration without an ADR.

Failure discipline: categorical safe errors, fail closed on authorization, preserve negative tests, avoid unrelated changes. Human review is not purchase authorization.
