"""Local EDGE inquiry companion.

Runs only on loopback. It accepts validated corpus JSON, uses a verified
Ollama model, persists reports and Free-tier usage locally, and never exposes
a cloud-facing API. Browser origins are opt-in and exact-match only.
"""
import hmac
import json
import os
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from intelligence.corpus import load_corpus_dict
from intelligence.inquiry_gateway import (
    run_user_inquiry, InquiryAccessDenied, InquiryQuotaExceeded,
)
from intelligence.store import ReportStore
from intelligence.usage_meter import SQLiteUsageStore
from intelligence.providers.ollama_local import OllamaLocalProvider, LocalModelError


MAX_BODY_BYTES = 5 * 1024 * 1024
DEFAULT_DATA_DIR = Path("data/local")


class LocalServiceError(RuntimeError):
    pass


def _read_or_create_secret(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise LocalServiceError("secret local invalide")
        return value
    value = secrets.token_urlsafe(32)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return value


def _read_or_create_installation_id(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_text(encoding="utf-8").strip()
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise LocalServiceError("identifiant local invalide")
        return value
    value = secrets.token_hex(32)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return value


def _allowed_origins(environ):
    raw = environ.get("EDGE_LOCAL_ALLOWED_ORIGINS", "")
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def build_local_provider(environ=None):
    env = os.environ if environ is None else environ
    if env.get("EDGE_LOCAL_LLM_ENABLED") != "1":
        raise LocalModelError("Ollama local desactive")
    model = env.get("EDGE_LOCAL_MODEL", "").strip()
    registry_path = env.get("EDGE_LOCAL_MODEL_REGISTRY", "data/local_model_registry.json")
    if not model:
        raise LocalModelError("EDGE_LOCAL_MODEL non configure")
    try:
        registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LocalModelError("registre de licence modele absent ou invalide") from exc
    if not isinstance(registry, dict):
        raise LocalModelError("registre de licence modele invalide")
    return OllamaLocalProvider(model=model, model_registry=registry, environ=env)


def execute_local_inquiry(payload, *, data_dir=DEFAULT_DATA_DIR, environ=None,
                          provider_factory=build_local_provider):
    env = os.environ if environ is None else environ
    if not isinstance(payload, dict):
        raise ValueError("objet JSON requis")
    question = payload.get("question")
    request_id = payload.get("request_id")
    corpus_payload = payload.get("corpus")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("question non vide de 2000 caracteres maximum requise")
    if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
        raise ValueError("request_id requis (128 caracteres maximum)")
    corpus = load_corpus_dict(corpus_payload)
    provider = provider_factory(env)
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    installation_id = _read_or_create_installation_id(root / "installation_id")
    usage_store = SQLiteUsageStore(str(root / "usage.sqlite3"))
    report_store = ReportStore(str(root / "intelligence"))
    return run_user_inquiry(
        question, [corpus], report_store,
        user_id=installation_id,
        request_id=request_id,
        usage_store=usage_store,
        provider=provider,
        subscription_claim=None,
    )


def create_handler(*, data_dir=DEFAULT_DATA_DIR, environ=None):
    env = dict(os.environ if environ is None else environ)
    root = Path(data_dir)
    token = _read_or_create_secret(root / "auth.token")
    allowed_origins = _allowed_origins(env)

    class Handler(BaseHTTPRequestHandler):
        server_version = "EDGE-Local/1.0"

        def log_message(self, fmt, *args):
            # Do not log request bodies, bearer tokens or user questions.
            return

        def _origin_allowed(self):
            origin = self.headers.get("Origin")
            if not origin:
                return True
            return origin.rstrip("/") in allowed_origins

        def _host_allowed(self):
            host = urlparse("//" + self.headers.get("Host", "")).hostname
            return host in {"127.0.0.1", "localhost", "::1"}

        def _authorized(self):
            supplied = self.headers.get("Authorization", "")
            return supplied.startswith("Bearer ") and hmac.compare_digest(
                supplied[7:].encode("utf-8"), token.encode("utf-8")
            )

        def _report_store(self):
            return ReportStore(str(root / "intelligence"))

        def _report_entries(self):
            entries = self._report_store().load_index().get("reports", [])
            public_fields = (
                "report_id", "report_version", "title", "market", "region",
                "created_at", "production_status", "simulated",
                "verification_level", "label", "edge_decision", "data_as_of",
            )
            return [{key: entry[key] for key in public_fields if key in entry}
                    for entry in sorted(entries, key=lambda item: item.get("created_at", ""), reverse=True)]

        def _read_report(self, report_id, version):
            store = self._report_store()
            report = store.read(report_id, version)
            index_entries = [
                entry for entry in store.load_index().get("reports", [])
                if entry.get("report_id") == report_id
                and entry.get("report_version") == report.get("report_version")
            ]
            dossier = None
            if index_entries and index_entries[0].get("dossier_path"):
                base = Path(store.root).resolve()
                dossier_path = (base / index_entries[0]["dossier_path"]).resolve()
                if base not in dossier_path.parents:
                    raise ValueError("chemin de dossier invalide")
                with dossier_path.open(encoding="utf-8") as handle:
                    dossier = json.load(handle)
            return {"status": "REPORT", "report": report, "dossier": dossier}

        def _send_json(self, status, body, cors=False):
            raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            origin = self.headers.get("Origin")
            if cors and origin and origin.rstrip("/") in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            if not self._host_allowed() or not self._origin_allowed():
                return self._send_json(403, {"error": "origin_or_host_denied"})
            origin = self.headers.get("Origin")
            if not origin:
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Max-Age", "300")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()

        def do_GET(self):
            if not self._host_allowed() or not self._origin_allowed():
                return self._send_json(403, {"error": "origin_or_host_denied"})
            parsed = urlparse(self.path)
            if parsed.path == "/v1/reports" or parsed.path.startswith("/v1/reports/"):
                if not self._authorized():
                    return self._send_json(401, {"error": "unauthorized"}, cors=True)
                try:
                    if parsed.path == "/v1/reports":
                        return self._send_json(200, {"reports": self._report_entries()}, cors=True)
                    report_id = parsed.path[len("/v1/reports/"):]
                    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", report_id):
                        return self._send_json(400, {"error": "invalid_report_id"}, cors=True)
                    query = parse_qs(parsed.query)
                    version_values = query.get("version", [])
                    version = None
                    if version_values:
                        if len(version_values) != 1 or not version_values[0].isdigit() or int(version_values[0]) < 1:
                            return self._send_json(400, {"error": "invalid_report_version"}, cors=True)
                        version = int(version_values[0])
                    result = self._read_report(report_id, version)
                    return self._send_json(200, result, cors=True)
                except KeyError:
                    return self._send_json(404, {"error": "report_not_found"}, cors=True)
                except (ValueError, OSError, json.JSONDecodeError):
                    return self._send_json(500, {"error": "report_read_failed"}, cors=True)
            if parsed.path != "/health":
                return self._send_json(404, {"error": "not_found"})
            if env.get("EDGE_LOCAL_LLM_ENABLED") != "1":
                return self._send_json(200, {
                    "service": "edge-local", "status": "model_disabled", "provider": None,
                }, cors=True)
            try:
                build_local_provider(env)
            except LocalModelError:
                return self._send_json(200, {
                    "service": "edge-local", "status": "model_not_configured", "provider": None,
                }, cors=True)
            return self._send_json(200, {
                "service": "edge-local", "status": "configured", "provider": "ollama_local",
            }, cors=True)

        def do_POST(self):
            if not self._host_allowed() or not self._origin_allowed():
                return self._send_json(403, {"error": "origin_or_host_denied"})
            if urlparse(self.path).path != "/v1/inquiry":
                return self._send_json(404, {"error": "not_found"})
            if not self._authorized():
                return self._send_json(401, {"error": "unauthorized"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._send_json(400, {"error": "invalid_content_length"})
            if length < 1 or length > MAX_BODY_BYTES:
                return self._send_json(413, {"error": "request_too_large_or_empty"})
            if "application/json" not in self.headers.get("Content-Type", "").lower():
                return self._send_json(415, {"error": "application_json_required"})
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = execute_local_inquiry(
                    payload, data_dir=data_dir, environ=env
                )
                return self._send_json(200, result, cors=True)
            except InquiryQuotaExceeded as exc:
                return self._send_json(429, {"error": str(exc)}, cors=True)
            except (ValueError, InquiryAccessDenied) as exc:
                return self._send_json(400, {"error": str(exc)}, cors=True)
            except LocalModelError:
                return self._send_json(503, {"error": "local_model_not_ready"}, cors=True)
            except Exception as exc:
                # Deliberately omit exception details and filesystem paths.
                return self._send_json(500, {"error": "local_inquiry_failed"}, cors=True)

    return Handler


def serve(host="127.0.0.1", port=8765, data_dir=DEFAULT_DATA_DIR, environ=None):
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise LocalServiceError("le service EDGE local doit ecouter uniquement sur loopback")
    handler = create_handler(data_dir=data_dir, environ=environ)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    print(f"EDGE Local ecoute sur http://{host}:{port} (loopback uniquement)")
    print(f"Jeton local : {Path(data_dir) / 'auth.token'}")
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Service local EDGE / Ollama")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    args = parser.parse_args()
    serve(args.host, args.port, args.data_dir)
