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

## Token economy — optimize waste, never quality

### Priority hierarchy (mandatory)
Correctness, security, data integrity, functional completeness and maintainability outrank token savings. Then optimize execution efficiency, then communication brevity. Never reduce implementation scope, necessary investigation, reasoning depth, tests, accessibility, error handling or documentation merely to meet a token target. Do not choose an inferior solution because it is shorter. Avoid unnecessary complexity as well as premature simplification.

### Separate budgets
- Communication: target 900 characters / 120 words for routine reports; 1600 characters / 220 words for substantial deliveries. These are soft ceilings, not truncation rules. Exceed whenever necessary for accuracy, material risks, blockers, decisions, evidence or an explicit request for detail. Use compact Delivered / Validation / Blockers / Next fields; omit empty fields. No filler, repeated context, decorative diagrams or repeated plans.
- Exploration: retrieve targeted context and batch independent reads when safe. Reuse verified unchanged information, but re-read whenever correctness, concurrent changes, unfamiliar code or stale context warrants it. Never assume unseen code or skip relevant dependencies.
- Production and reasoning: no arbitrary character, token, file, commit, test or tool-call cap. Use the effort needed to deliver the complete vertical slice. Prefer coherent changes over artificial micro-deliveries. Run appropriate unit, integration and user-journey tests; disclose unexecuted checks. Do not weaken tests to pass.
- Durable handoff: no chat-length cap applies to code, tests, technical documentation or PROJECT_STATE.md. Preserve enough evidence and context for another agent to resume independently.

### Resource exhaustion
If a real provider quota, context limit or execution budget approaches, preserve coherent work, record exact progress, unfinished tasks and validation in the canonical handoff, and resume from there. Never silently downgrade quality, fake completion, truncate essential code or omit validation. For application-owned agents, measure input/output usage and use task-specific budgets, bounded retries and explicit escalation; never silently truncate evidence or substitute a cheaper model where it fails quality criteria. Do not claim control of external ChatGPT quotas or hidden reasoning.

### Final quality gate
Before finishing, ask: is the requested outcome actually usable, are important failure paths covered, and could another agent reproduce or resume the work? If not, continue when feasible or report the precise blocker. Then remove only redundant communication. A bare "Go" means execute, not repeat the roadmap. Token efficiency is measured per successfully delivered outcome, not per short response.

## Mandatory productive-response gate
For an authorized development request (including "Go"), do not end the turn with a statement of intent, repeated roadmap, generic progress report, or a description of an already-known gap. Continue executing until there is a material, persisted project improvement with evidence, or a genuinely unavoidable blocker. Reading files alone is not delivery. A newly discovered blocker is reportable only after reasonable targeted attempts to resolve it and consideration of independent useful work; report the exact failed operation, evidence, and minimum owner action if needed. Do not manufacture trivial commits or unnecessary documentation to satisfy this gate. If a meaningful implementation is feasible, implement and validate it before reporting. Never claim background work, completion, or tests that did not occur. Explicit questions about strategy, status or explanation remain answerable directly with new useful information. Quality and safety gates remain mandatory. This is an agent operating rule, not a claim of runtime enforcement over external AI interfaces.
