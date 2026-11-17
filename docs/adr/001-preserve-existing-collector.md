# ADR 001 — Preserve existing collector while defining V1 contracts

Status: Proposed; requires client approval.

## Context
The existing repository contains an immutable Cloudflare D1 collector, an investigation validation boundary, and a Next.js/OpenNext UI. The desired target is Workers + D1 + TypeScript + static SPA. Replacing the whole application now risks breaking working data paths.

## Options
A. Preserve the collector and investigation boundary; evolve the UI separately behind explicit contracts.
B. Replace the application and data pipeline in one rewrite.

## Decision
Prefer **A**, provisionally; no migration is authorized by this ADR alone.

## Rationale
Smaller blast radius, reversible delivery, independent testability, preserved observation provenance.

## Consequences
The repository temporarily has a target-vs-current UI mismatch; a later ADR must decide migration mechanics. No production change.

## Reversibility
Revisit after CI-backed API and SPA prototype comparison; revert development-branch changes without modifying D1 history.
