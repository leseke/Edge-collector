"""Offline tests for the loopback-only EDGE local companion."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

from intelligence.local_service import (
    LocalServiceError, _read_or_create_secret, create_handler, serve,
)
from intelligence.inquiry_gateway import InquiryQuotaExceeded


class LocalServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.handler = create_handler(
            data_dir=self.root,
            environ={"EDGE_LOCAL_ALLOWED_ORIGINS": "https://edge.example"},
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.token = (self.root / "auth.token").read_text().strip()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, path, *, method="GET", body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = Request(self.base + path, data=data, headers=headers or {}, method=method)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, response.headers, response.read()
        except HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_health_does_not_claim_model_is_ready_when_disabled(self):
        status, _, raw = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["status"], "model_disabled")

    def test_health_does_not_claim_configured_without_model_registry(self):
        handler = create_handler(
            data_dir=self.root / "enabled",
            environ={"EDGE_LOCAL_LLM_ENABLED": "1", "EDGE_LOCAL_MODEL": "missing-model",
                     "EDGE_LOCAL_MODEL_REGISTRY": str(self.root / "missing.json")},
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            req = Request(f"http://127.0.0.1:{server.server_port}/health")
            with urlopen(req, timeout=3) as response:
                body = json.loads(response.read())
            self.assertEqual(body["status"], "model_not_configured")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_inquiry_requires_bearer_token(self):
        status, _, raw = self.request(
            "/v1/inquiry", method="POST",
            body={"question": "Pokémon", "request_id": "r1", "corpus": {}},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(raw)["error"], "unauthorized")

    @patch("intelligence.local_service.execute_local_inquiry", return_value={"status": "NO_DATA"})
    def test_authorized_inquiry_calls_local_runtime(self, execute):
        status, _, raw = self.request(
            "/v1/inquiry", method="POST",
            body={"question": "Pokémon", "request_id": "r1", "corpus": {}},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["status"], "NO_DATA")
        execute.assert_called_once()

    @patch("intelligence.local_service.execute_local_inquiry", side_effect=InquiryQuotaExceeded("quota atteint"))
    def test_quota_exhaustion_returns_http_429(self, execute):
        status, _, raw = self.request(
            "/v1/inquiry", method="POST",
            body={"question": "Pokémon", "request_id": "r1", "corpus": {}},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        self.assertEqual(status, 429)
        self.assertEqual(json.loads(raw)["error"], "quota atteint")

    def test_unlisted_browser_origin_is_rejected(self):
        status, _, raw = self.request(
            "/v1/inquiry", method="POST",
            body={"question": "Pokémon"},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
                "Origin": "https://evil.example",
            },
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(raw)["error"], "origin_or_host_denied")

    def test_preflight_allows_only_configured_origin_and_private_network(self):
        status, headers, _ = self.request(
            "/v1/inquiry", method="OPTIONS",
            headers={"Origin": "https://edge.example"},
        )
        self.assertEqual(status, 204)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://edge.example")
        self.assertEqual(headers.get("Access-Control-Allow-Private-Network"), "true")

    def test_unknown_origin_preflight_is_rejected(self):
        status, _, _ = self.request(
            "/v1/inquiry", method="OPTIONS",
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(status, 403)

    def test_unknown_route_is_not_found(self):
        status, _, _ = self.request("/admin")
        self.assertEqual(status, 404)

    def test_secret_is_persistent(self):
        path = self.root / "other" / "token"
        first = _read_or_create_secret(path)
        second = _read_or_create_secret(path)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 32)

    def test_server_refuses_non_loopback_bind(self):
        with self.assertRaises(LocalServiceError):
            serve(host="0.0.0.0", port=0, data_dir=self.root)


if __name__ == "__main__":
    unittest.main()
