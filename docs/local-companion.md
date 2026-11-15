# EDGE Local Companion (Ollama)

## What this is

A local-only companion for the static EDGE website. It runs the inquiry engine
on the computer where Ollama is installed, rather than pretending that a
Vercel serverless function can reach the user's local Ollama process.

The service:
- binds only to `127.0.0.1` by default and refuses non-loopback bind addresses;
- accepts only validated `edge.corpus.v1` JSON and a bounded question;
- requires a random bearer token stored in `data/local/auth.token`;
- persists a local installation identifier and Free investigation quota in
  `data/local/`;
- uses the existing immutable `ReportStore`;
- refuses to run without an explicitly enabled Ollama adapter and a local
  model registry entry whose commercial licence, licence ID and SHA-256 digest
  have been verified by the operator;
- does not download models, call remote AI APIs, or make purchases.

This is a single-installation local Free runtime. It is **not** a multi-user
subscription backend, payment integration, or production cloud API. Premium
claims must still come from a trusted billing backend; no browser-provided
claim is accepted here.

## Requirements

- Python 3.10+
- Dependencies from `requirements.txt` (the Ollama HTTP client uses the
  existing `requests` dependency)
- Ollama installed and running locally
- A model already downloaded locally
- The model's exact licence and commercial-use permission verified by the
  operator. Do not mark a model VERIFIED based on an assumption.

## Configure the local model

Create `data/local_model_registry.json` with an entry keyed by the exact
Ollama model tag. Only enter values after checking the model card and licence:

```json
{
  "EXACT_MODEL_TAG": {
    "status": "VERIFIED",
    "commercial_use": true,
    "license_id": "EXACT_LICENSE_IDENTIFIER",
    "digest": "sha256:VERIFIED_MODEL_DIGEST"
  }
}
```

The example values above are placeholders, not a model recommendation or
verification. Keep this file local and out of Git.

PowerShell:

```powershell
$env:EDGE_LOCAL_LLM_ENABLED = "1"
$env:EDGE_LOCAL_MODEL = "EXACT_MODEL_TAG"
$env:EDGE_LOCAL_MODEL_REGISTRY = "data/local_model_registry.json"
python -m intelligence.local_service
```

Linux/macOS:

```sh
export EDGE_LOCAL_LLM_ENABLED=1
export EDGE_LOCAL_MODEL='EXACT_MODEL_TAG'
export EDGE_LOCAL_MODEL_REGISTRY='data/local_model_registry.json'
python -m intelligence.local_service
```

The service listens on `http://127.0.0.1:8765`. Its bearer token is generated
once and stored with owner-only permissions at `data/local/auth.token`.
Do not share that token or commit it.

## Optional browser origin

Browser access is disabled unless an exact origin is configured. If and only
if the EDGE website origin is known and trusted, set it explicitly before
starting the service:

```powershell
$env:EDGE_LOCAL_ALLOWED_ORIGINS = "https://YOUR-EXACT-EDGE-ORIGIN"
```

Multiple exact origins may be comma-separated. Wildcards, suffix matching,
and arbitrary origins are not supported. The browser must send the bearer
token in the Authorization header. Local-network access permissions may also
be requested by the browser. Do not weaken the loopback bind or origin checks
to work around a browser permission prompt.

## API

- `GET /health`: local service status only; reports `model_disabled` until
  enabled, then `configured` only when the exact model has a valid local
  licence-registry entry. It does not prove that the Ollama daemon is running.
- `POST /v1/inquiry`: requires `Authorization: Bearer <token>` and
  `Content-Type: application/json`.

Request body:

```json
{
  "request_id": "unique-client-generated-id",
  "question": "Analyse cette opportunité Pokémon TCG",
  "corpus": {
    "corpus_schema": "edge.corpus.v1"
  }
}
```

The abbreviated corpus above is intentionally invalid; send a complete corpus
that passes `intelligence.corpus.load_corpus_dict`. The maximum request body is
5 MiB. Request identifiers are quota-idempotent; callers must also deduplicate
in-flight requests if they require response-level idempotence.

## Persistence and limitations

- Reports: `data/local/intelligence/`
- Usage quota: `data/local/usage.sqlite3`
- Installation identity: `data/local/installation_id`
- Local bearer token: `data/local/auth.token`

Back up the data directory securely. Do not place it in a public web root.
SQLite is suitable here only for this single local installation. This
The browser transport helper `assets/edge-local.mjs` is available, but it is
not yet connected to a visible UI flow and does not persist the bearer token.
This companion does not implement cloud identity, Stripe/webhooks,
multi-instance quota coordination, Premium billing, or a complete browser UI.
Those require a separate trusted server backend and must not be simulated in client code.
