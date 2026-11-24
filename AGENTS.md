# EDGE — mandatory operating contract for every agent

Read this file, docs/PROJECT_STATE.md and docs/ROADMAP.md before working, regardless of model, conversation, automation or tool. Repository state is authoritative; chat summaries are not. Explicit owner instructions take precedence. Do not silently change this contract.

## Mission
Deliver a complete, professional, autonomous TCG market-intelligence web application usable daily in France. Detect asymmetric opportunities early, across TCG markets, using real observations, historical patterns, commercial events and reasoned hypotheses. Risk is not a reason to reject a preshot automatically. No fabricated market data, no invented sales, no conflation of asking prices and transactions.

## Mandatory execution loop
1. Read the three canonical files and inspect current branch HEAD, open PR and relevant existing code. Check for concurrent changes before writing. Do not recreate existing files.
2. Select the highest-priority unfinished user-facing outcome in the roadmap. Audit only what is needed to unblock delivery; group related changes into a coherent vertical slice (data, logic, interface, tests).
3. Implement actual code. Do not end a normal authorized development session with only a plan, repetitive audit or promises if implementation is feasible. Reuse existing modules. Do not introduce unnecessary architecture or dependencies.
4. Run meaningful tests against production code, not just string assertions. Verify the exact final SHA and report pending/skipped tests honestly. Never claim a browser journey or deployment was tested unless it was.
5. Update docs/PROJECT_STATE.md with actual changes, remaining gaps, evidence links, exact code commit(s), test results and the next executable task. Record pending CI explicitly; do not claim a state-file commit SHA in its own contents. Keep the roadmap current. This handoff is required before ending a development session.
6. Report in French: what the user can now do, what was actually delivered, validation, blockers, and next action. Avoid repetitive plans and micro-commit reports.

## Non-negotiable constraints
- TCG and direct ecosystem only; international opportunities accessible in France.
- Real data and provenance; unknown is not zero. Distinguish facts, weak signals, inferences and bets. Integrity hashes do not establish commercial truth.
- No manual user input when reliable automated collection is feasible. Do not confuse local experimental AI with autonomous production AI.
- No paid services, secrets in code, unauthorized purchases or financial commitments.
- Work on the approved development branch; never merge, alter main, deploy production, or delete branches without explicit owner authorization. Preview and offline tests permitted.
- No false claims of completion. A feature is delivered only when connected to the real user journey, with honest empty/error states and relevant tests.
- If blocked by permissions or missing data, implement safe independent work and document the exact blocker. Ask the owner only when necessary.
- Changes to this operating contract, scope or major architectural direction require explicit owner approval. Other agents must not replace it with their own workflow.

## Resume
A bare “Go” authorizes continuing the highest-priority safe development task, not restarting planning. Read the canonical state and inspect actual HEAD. If they disagree, reconcile from repository evidence.
