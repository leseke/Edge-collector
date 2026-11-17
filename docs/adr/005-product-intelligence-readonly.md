# ADR 005 — Read-only product intelligence page

Status: Implemented on development branch; CI and mobile rendering pending.

## Context
The observed Explorer needs a product-level destination before contextual AI or a complete catalogue can be attached.

## Options
A. Add a dynamic product route using only the integrity-checked existing market snapshot.
B. Add a new database and vendor API for product detail before provenance and budget controls are defined.
C. Display speculative AI ratings and fabricated charts as placeholders.

## Decision
Choose A. Dynamic route `/explorer/[productId]` looks up the observed product ID in the verified snapshot, rejects unknown IDs with 404, and exposes price provenance and explicit uncertainty. No purchase, AI invocation, D1 mutation or new external data provider.

## Follow-up
Investigate asset image source failures, product variants, actual completed sales, and an authorized backend AI gateway with quotas and human review. These are not delivered by this ADR.

## Reversibility
Delete the detail route and remove product links and related styles. No persistent schema changes.
