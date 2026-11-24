# EDGE — TCG Market Intelligence

EDGE is a market-intelligence and decision-support project focused on trading
card games and their direct ecosystem.

## Local AI companion

The static web interface includes an experimental local inquiry page at
`/local/`. It connects to a loopback-only Python companion and an explicitly
configured Ollama model. It does not use a remote AI API.

Read [the local companion setup guide](docs/local-companion.md) before enabling
it. Model licensing, commercial-use permission, local secrets and browser
origin allowlisting must be configured deliberately. No model is selected or
enabled by default.

## Development and safety

- Keep paid provider calls behind the existing SpendGuard controls.
- Do not accept subscription claims or user identities from browser input.
- Do not treat listing prices as realized sales.
- Preserve provenance and distinguish facts, weak signals, inferences and bets.
- Keep generated/demo data visibly separate from observed market data.
