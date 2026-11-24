"""End-to-end contract checks for the public TCG observation corpus and local validator.

These fixtures are explicitly synthetic *test inputs*, never market observations.
"""
import copy
import json
import shutil
import subprocess
from pathlib import Path
import unittest

from intelligence.corpus import CorpusRejected, load_corpus_dict


def sample_export():
    """Mirror the fields emitted by TcgCorpusDownload.makeCorpus."""
    return {
        "corpus_schema": "edge.corpus.v1",
        "corpus_id": "tcg_20261120-1234",
        "simulated": False,
        "data_as_of": "2026-11-20T12:00:00.000Z",
        "subject": {"title": "TEST CARD — synthetic fixture", "market": "TCG",
                    "category": "tcg", "region": "GLOBAL"},
        "entities": ["TEST CARD — synthetic fixture"],
        "topics": [{"topic_id": "market_evidence",
                    "question": "Quelles observations sont disponibles et quelles preuves manquent ?",
                    "keywords": ["TCG", "prix", "provenance"]}],
        "sources": [{
            "source_id": "src_capture",
            "title": "Relevé commercial EDGE 20261120-1234",
            "publisher": "EDGE — collecte déclarée",
            "url": "https://raw.githubusercontent.com/leseke/Edge-collector/edge/commercial-history/snapshots/20261120-1234/report.json",
            "published_at": None, "accessed_at": "2026-11-20",
            "tier": "unverified", "simulated": False,
            "notes": "Test fixture. Integrity hash is not proof of a completed sale.",
        }],
        "datasets": [{
            "dataset_id": "ds_indicative",
            "title": "Indication basse agrégée non vérifiée (pas une vente conclue)",
            "unit": "currency", "currency": "EUR", "measure": "other",
            "territory": "GLOBAL",
            "period": {"start": "2026-11-20", "end": "2026-11-20"},
            "frequency": "irregular",
            "provenance": {"source_ids": ["src_capture"],
                           "method": "Indication agrégée déclarée. Aucune preuve de transaction.",
                           "collected_by": "collector"},
            "simulated": False,
            "points": [{"t": "2026-11-20", "value": 12.5, "status": "estimated"}],
        }],
        "dataset_topics": {"ds_indicative": ["market_evidence"]},
        "extracts": [],
    }


class TcgCorpusHandoffTests(unittest.TestCase):
    def test_history_typescript_contract(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js 24 required")
        major = int(subprocess.check_output([node, "--version"], text=True).strip().lstrip("v").split(".")[0])
        if major < 24:
            self.skipTest("Node.js 24 required")
        root = Path(__file__).resolve().parents[1]
        subprocess.run([node, str(root / "tests/tcg_history_contract.mjs")], cwd=root, check=True, timeout=20)

    def test_production_typescript_output(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js 24 required for TypeScript contract test")
        major = int(subprocess.check_output([node, "--version"], text=True).strip().lstrip("v").split(".")[0])
        if major < 24:
            self.skipTest("Node.js 24 required for TypeScript contract test")
        root = Path(__file__).resolve().parents[1]
        output = subprocess.check_output([node, str(root / "tests/tcg_corpus_contract.mjs")], cwd=root, text=True, timeout=20)
        priced, missing = map(load_corpus_dict, json.loads(output))
        self.assertEqual(priced.datasets["ds_indicative"]["points"][0]["status"], "estimated")
        self.assertEqual(priced.datasets["ds_indicative"]["measure"], "other")
        self.assertEqual(missing.datasets, {})

    def test_export_contract_is_accepted_by_real_validator(self):
        corpus = load_corpus_dict(sample_export())
        self.assertEqual(corpus.corpus_id, "tcg_20261120-1234")
        self.assertEqual(corpus.datasets["ds_indicative"]["measure"], "other")
        self.assertEqual(corpus.datasets["ds_indicative"]["points"][0]["status"], "estimated")

    def test_missing_price_keeps_empty_datasets_and_no_sales(self):
        payload = sample_export()
        payload["datasets"] = []
        payload["dataset_topics"] = {}
        corpus = load_corpus_dict(payload)
        self.assertEqual(corpus.datasets, {})
        self.assertEqual(corpus.extracts, {})

    def test_invalid_provenance_is_rejected(self):
        payload = copy.deepcopy(sample_export())
        payload["datasets"][0]["provenance"]["source_ids"] = ["src_unknown"]
        with self.assertRaises(CorpusRejected):
            load_corpus_dict(payload)

    def test_fake_sale_dataset_is_rejected_if_source_is_missing(self):
        payload = copy.deepcopy(sample_export())
        payload["datasets"][0]["measure"] = "sold_price"
        payload["datasets"][0]["provenance"]["source_ids"] = ["src_unknown"]
        with self.assertRaises(CorpusRejected):
            load_corpus_dict(payload)


if __name__ == "__main__":
    unittest.main()
