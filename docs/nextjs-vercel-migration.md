# EDGE Next.js / Vercel bridge

This branch adds a Next.js App Router host while preserving the existing browser UI
as static assets under `public/legacy`. The dashboard, MRI and local inquiry screens
are served through same-origin iframe routes during this compatibility phase.

## Commands

- `npm install`
- `npm run typecheck`
- `npm run build`
- `npm run dev`

## Routes

- `/` — existing market dashboard
- `/mri` — existing Market Reaction Intelligence screen
- `/local` — existing local Ollama inquiry screen

The legacy browser modules are copied to `public/legacy/assets`. They retain their
existing data-source behavior and provenance checks. The market data feed remains
read from the configured public GitHub snapshot source; this Next.js shell does not
create a new backend or claim to connect the local Ollama service to a cloud runtime.

## Important limitations

- This is a migration bridge, not a full React rewrite.
- The local Ollama companion still runs on the user's own computer and requires an
  exact allowed-origin entry for the deployed EDGE origin.
- No remote AI provider, paid API, billing, account system, or cloud database is enabled.
- The old static interface remains available in the repository root for rollback.
