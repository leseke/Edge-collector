# EDGE × DeepSeek Harness — isolated integration pilot

DeepSeek Harness is an upstream developer-preview agent runtime (https://github.com/deepseek-ai/deepseek-harness). It is **not** bundled, deployed, or granted access to EDGE infrastructure here.

## Architecture

1. EDGE collector and D1 remain the source of truth. No agent can edit immutable market observations.
2. A future DeepSeek Harness plugin calls a *read-only, allowlisted* EDGE data tool. The runtime never receives Cloudflare/GitHub credentials.
3. The agent returns a typed proposal (facts, weak signals, inferences, thesis, catalysts, risks, entry and exit hypotheses).
4. EDGE validates and records the proposal separately from verified observations; promotion and purchasing require explicit human approval.

This pilot implements the **typed boundary and validation** independently of the upstream harness, to avoid relying on unstable plugin APIs. No API key, external model request, order, payment or paid service is used.

## Local verification

`node --test agent-harness/test/*.test.mjs`

## Next integration gate

In a separate sandbox, pin an upstream dsh release/commit, inspect its actual plugin API and safety model, then write a minimal plugin that calls EDGE's read-only interface. Keep it disabled by default until a security and cost review passes.
