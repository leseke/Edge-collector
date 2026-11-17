# EDGE — product scope, V1 working specification

Status: **DRAFT**, awaiting explicit acceptance. This document records the user-agreed direction, not a claim of complete implementation.

## Goal
Discover and investigate potential asymmetries in TCG collectible markets before consensus forms. Support rational preshot risk without requiring completed sales or proven demand. Design boundaries to allow other collectible categories later without committing to a V1 expansion.

## Evidence
Keep timestamped, attributed observations; distinguish LISTING, AGGREGATE, COMPLETED_SALE. Preserve FACT, WEAK_SIGNAL, INFERENCE, BET. Never confuse synthetic samples, listed prices, indicative aggregates, and realized transactions. A citation match is not proof of claim semantics.

## Investigation
A proposal identifies product, thesis, catalysts, risks, entry hypothesis, exit hypothesis, and evidence. Lack of data is an explicit gap, not automatic rejection. Price and demand claims require independent validation.

## Human control
All proposals require human review. Review does not authorize purchasing; no autonomous checkout, ordering, or payment. No paid inference or external data transfer without explicit operator opt-in.

## Delivery boundaries
Target stack: Cloudflare Workers + D1 + TypeScript + static SPA. The current repository includes Next.js/OpenNext, so migration to the target UI stack is **not decided**. Preserve main and production. Use branch-only changes, reproducible tests, approved CI and ADRs.

## Explicitly unresolved
Authentication and roles, durable review-event schema, API contracts, retention, deployment promotion, model provider/cost policy, exact V1 category boundary. These are not silently assumed.
