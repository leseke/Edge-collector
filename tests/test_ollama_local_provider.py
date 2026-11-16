"""Offline tests for the local Ollama adapter; no server/network required."""
import unittest

from intelligence.providers.ollama_local import (
    OllamaLocalProvider, LocalModelError, _decode, _local_endpoint,
)


MODEL = {
    "llama-test": {
        "status": "VERIFIED",
        "commercial_use": True,
        "license_id": "Apache-2.0",
        "digest": "sha256:" + "a" * 64,
    }
}


class OllamaLocalProviderTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with self.assertRaises(LocalModelError):
            OllamaLocalProvider("llama-test", MODEL, environ={})

    def test_unverified_license_is_rejected(self):
        with self.assertRaises(LocalModelError):
            OllamaLocalProvider("llama-test", {"llama-test": dict(MODEL["llama-test"], status="UNVERIFIED")},
                                environ={"EDGE_LOCAL_LLM_ENABLED": "1"})

    def test_noncommercial_license_is_rejected(self):
        with self.assertRaises(LocalModelError):
            OllamaLocalProvider("llama-test", {"llama-test": dict(MODEL["llama-test"], commercial_use=False)},
                                environ={"EDGE_LOCAL_LLM_ENABLED": "1"})

    def test_missing_digest_is_rejected(self):
        with self.assertRaises(LocalModelError):
            OllamaLocalProvider("llama-test", {"llama-test": dict(MODEL["llama-test"], digest="")},
                                environ={"EDGE_LOCAL_LLM_ENABLED": "1"})

    def test_remote_endpoint_is_rejected(self):
        for url in ("https://api.example.com/api/chat", "http://192.168.1.4:11434/api/chat",
                    "http://127.0.0.1:8080/api/chat"):
            with self.assertRaises(LocalModelError):
                _local_endpoint(url)

    def test_only_local_ollama_endpoint_is_allowed(self):
        self.assertEqual(_local_endpoint("http://127.0.0.1:11434/api/chat"),
                         "http://127.0.0.1:11434/api/chat")
        self.assertEqual(_local_endpoint("http://localhost:11434/api/chat"),
                         "http://localhost:11434/api/chat")

    def test_bad_json_response_is_rejected(self):
        with self.assertRaises(LocalModelError):
            _decode({"message": {"content": "not-json"}})

    def test_model_is_called_only_after_explicit_enable_and_valid_license(self):
        calls = []
        def fake_send(payload):
            calls.append(payload)
            return {"message": {"content": '{"topic_ids": [], "notes": "offline test"}'}}
        provider = OllamaLocalProvider("llama-test", MODEL,
                                       environ={"EDGE_LOCAL_LLM_ENABLED": "1"}, send=fake_send)
        result = provider._request("plan", {"type": "object"}, {"question": "test"}, 100)
        self.assertEqual(result["topic_ids"], [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(provider.paid, False)


if __name__ == "__main__":
    unittest.main()
