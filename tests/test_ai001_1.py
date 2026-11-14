"""AI-001.1 : tests negatifs ecrits AVANT correction (fraicheur, integrite,
verification des faits, contrat de depense). Aucun reseau."""
import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from intelligence.store import ReportStore, next_version
from intelligence.validator import assess, content_sha256
from tests.test_intelligence import load, real_report, setUpModule, tearDownModule  # noqa: F401 (sockets bloques)

T0 = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
LATER = datetime(2027, 3, 1, tzinfo=timezone.utc)


def with_record(r):
    """Ajoute une trace de verification documentee a chaque fait verifie."""
    for c in r["claims"]:
        if c["verification"] == "verified":
            c["verification_record"] = {
                "verified_by": {"role": "human", "id": "fondateur"},
                "verified_at": "2026-10-18T10:00:00+00:00", "method": "primary_document_review",
                "procedure": "EVP-1",
                "evidence": [{"source_id": c["source_ids"][0], "locator": "page produit, section prix"}]}
    return r


# ------------------------------------------------------------ 1. fraicheur
class FreshnessTests(unittest.TestCase):
    def test_verified_report_not_current_once_data_is_old(self):
        r = with_record(real_report())
        r["freshness"] = {"max_data_age_days": 30}
        now_ = assess(r, now=T0)
        later = assess(r, now=LATER)
        self.assertEqual(now_["verification_level"], later["verification_level"])  # fiabilite inchangee
        self.assertEqual(now_["timeliness"]["status"], "current")
        self.assertEqual(later["timeliness"]["status"], "stale")
        self.assertIn("PERIME", later["display_label"])
        self.assertNotIn("PERIME", now_["display_label"])

    def test_absent_policy_is_prudent(self):
        r = with_record(real_report())
        r.pop("freshness", None)
        t = assess(r, now=LATER)["timeliness"]
        self.assertEqual(t["policy"], "default")
        self.assertEqual(t["status"], "stale")
        self.assertEqual(assess(r, now=T0)["timeliness"]["status"], "current")

    def test_timeliness_boundary_and_future_consultation_date(self):
        r = with_record(real_report())
        r["freshness"] = {"max_data_age_days": 30}
        edge = datetime(2026, 11, 14, tzinfo=timezone.utc)  # 30 j apres data_as_of (15/10)
        self.assertEqual(assess(r, now=edge)["timeliness"]["status"], "current")
        self.assertEqual(assess(r, now=datetime(2026, 11, 15, 0, 0, 1, tzinfo=timezone.utc))["timeliness"]["status"], "stale")
        before = assess(r, now=datetime(2026, 1, 1, tzinfo=timezone.utc))["timeliness"]
        self.assertEqual(before["status"], "unknown")  # consultation anterieure aux donnees : incoherent

    def test_index_carries_what_dashboard_needs(self):
        with tempfile.TemporaryDirectory() as d:
            e = ReportStore(os.path.join(d, "i")).publish(load())
        self.assertEqual(e["data_as_of"], load()["data_as_of"])
        self.assertEqual(e["max_data_age_days"], 30)
        self.assertEqual(e["freshness_policy"], "declared")


# ------------------------------------------------------------ 2. integrite
class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = ReportStore(os.path.join(self.tmp.name, "intel"))
        self.v1, self.v2 = load(), load("pokemon_china_fictif.v2.json")
        self.s.publish(self.v1)
        self.s.publish(self.v2)

    def tearDown(self):
        self.tmp.cleanup()

    def idx(self):
        return self.s.load_index()

    def save_idx(self, idx):
        with open(self.s.index_path, "w", encoding="utf-8") as f:
            json.dump(idx, f)

    def test_clean_store_has_no_problem(self):
        self.assertEqual(self.s.verify(), [])

    def test_orphan_file_detected(self):
        p = os.path.join(self.s.root, "reports", "eir_fantome", "v0001.json")
        os.makedirs(os.path.dirname(p))
        with open(p, "w", encoding="utf-8") as f:
            f.write("{}")
        self.assertTrue(any("non reference" in x for x in self.s.verify()))

    def test_file_swapped_with_index_hash_updated(self):
        # v1 reecrite ET son empreinte mise a jour dans l'index : la chaine (v2.supersedes) le trahit
        forged = copy.deepcopy(self.v1)
        forged["subject"]["title"] = "Titre falsifie — EXEMPLE FICTIF"
        p = os.path.join(self.s.root, "reports", self.v1["report_id"], "v0001.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(forged, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        idx = self.idx()
        idx["reports"][0]["content_sha256"] = content_sha256(forged)
        self.save_idx(idx)
        self.assertTrue(any("chaine" in x for x in self.s.verify()))

    def test_entry_metadata_mismatch(self):
        idx = self.idx()
        idx["reports"][0]["production_status"] = "complete"
        idx["reports"][0]["verification_level"] = "fully_verified"
        self.save_idx(idx)
        self.assertTrue(any("metadonnee" in x for x in self.s.verify()))

    def test_file_identity_mismatch(self):
        idx = self.idx()
        idx["reports"][1]["path"] = idx["reports"][0]["path"]
        idx["reports"][1]["content_sha256"] = idx["reports"][0]["content_sha256"]
        self.save_idx(idx)
        self.assertTrue(any("identite" in x for x in self.s.verify()))

    def test_duplicate_and_gap(self):
        idx = self.idx()
        idx["reports"].append(dict(idx["reports"][0]))
        self.save_idx(idx)
        self.assertTrue(any("doublon" in x for x in self.s.verify()))
        idx = self.idx()
        idx["reports"] = [e for e in idx["reports"] if e["report_version"] != 1][:1]
        self.save_idx(idx)
        self.assertTrue(any("lacune" in x for x in self.s.verify()))

    def test_path_outside_store(self):
        idx = self.idx()
        idx["reports"][0]["path"] = "../../radar.json"
        self.save_idx(idx)
        self.assertTrue(any("chemin" in x for x in self.s.verify()))

    def test_corrupt_index(self):
        with open(self.s.index_path, "w", encoding="utf-8") as f:
            f.write("{pas du json")
        self.assertTrue(any("index illisible" in x for x in self.s.verify()))

    def test_external_anchor_detects_consistent_rewrite_of_last_version(self):
        anchor = self.s.fingerprint()  # a conserver hors du depot (racine de confiance)
        forged = copy.deepcopy(self.v2)
        forged["subject"]["title"] = "v2 falsifiee — EXEMPLE FICTIF"
        p = os.path.join(self.s.root, "reports", self.v2["report_id"], "v0002.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(forged, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        idx = self.idx()
        idx["reports"][1]["content_sha256"] = content_sha256(forged)
        idx["reports"][1]["title"] = forged["subject"]["title"]
        self.save_idx(idx)
        self.assertEqual(self.s.verify(), [])  # LIMITE : indetectable sans ancre externe
        self.assertTrue(any("ancre" in x for x in self.s.verify(expected_fingerprint=anchor)))


# ------------------------------------------------------------ 3. verification des faits
class FactVerificationTests(unittest.TestCase):
    def test_undocumented_verification_is_not_fully_verified(self):
        a = assess(real_report(), now=T0)
        self.assertTrue(a["valid"])  # compatibilite : rapport v1.0 toujours valide
        self.assertEqual(a["verification_level"], "partially_verified")
        self.assertTrue(any("non documentee" in w for w in a["warnings"]))
        self.assertEqual(assess(with_record(real_report()), now=T0)["verification_level"], "fully_verified")

    def test_record_rules(self):
        cases = [
            (lambda rec: rec["verified_by"].update(role="agent"), "agent"),
            (lambda rec: rec.update(evidence=[{"source_id": "src_absente", "locator": "x"}]), "preuve"),
            (lambda rec: rec.update(evidence=[]), "preuve"),
            (lambda rec: rec.update(verified_at="2027-01-01T00:00:00+00:00"), "verified_at"),
            (lambda rec: rec.update(method="intuition"), "hors de"),
            (lambda rec: rec.update(procedure=""), "trop court"),
        ]
        for mutate, needle in cases:
            r = with_record(real_report())
            mutate(r["claims"][0]["verification_record"])
            self.assertIn(needle, " | ".join(assess(r, now=T0)["errors"]), needle)

    def test_record_only_on_verified_facts(self):
        r = with_record(real_report())
        rec = r["claims"][0]["verification_record"]
        r["claims"][1]["verification"] = "unverified"
        r["production_status"] = "partial"
        r["claims"][1]["verification_record"] = rec
        self.assertIn("non verifiee", " | ".join(assess(r, now=T0)["errors"]))

    def test_promotion_creates_new_version_with_trace(self):
        from intelligence.factcheck import promote_claim
        r = real_report()
        r["production_status"] = "partial"
        r["claims"][0]["verification"] = "unverified"
        r["claims"][0].pop("verification_record", None)
        v2 = promote_claim(r, "clm_offre", verifier={"role": "human", "id": "fondateur"},
                           method="primary_document_review", procedure="EVP-1",
                           evidence=[{"source_id": "src_editeur-a", "locator": "fiche produit"}],
                           at="2026-10-20T08:00:00+00:00")
        self.assertEqual(v2["report_version"], 2)
        c = next(c for c in v2["claims"] if c["claim_id"] == "clm_offre")
        self.assertEqual(c["verification"], "verified")
        self.assertEqual(v2["history"]["corrections"][0]["target"], "$.claims[clm_offre]")
        self.assertTrue(assess(v2, now=T0)["valid"], assess(v2, now=T0)["errors"])
        with self.assertRaises(ValueError):
            promote_claim(r, "clm_offre", verifier={"role": "agent", "id": "llm"}, method="primary_document_review",
                          procedure="EVP-1", evidence=[{"source_id": "src_editeur-a", "locator": "x"}],
                          at="2026-10-20T08:00:00+00:00")


# ------------------------------------------------------------ 4. contrat de depense
class PaidProviderContractTests(unittest.TestCase):
    def setUp(self):
        from investigation.spend import SpendGuard
        self.tmp = tempfile.TemporaryDirectory()
        self.led = os.path.join(self.tmp.name, "spend.jsonl")
        self.guard = SpendGuard({"authorized": True, "max_usd_per_run": 0.5, "est_usd_per_call": 0.1},
                                ledger_path=self.led)
        self.guard.allow(["eir_agent-test"])
        self.inp = {"report_id": "eir_agent-test"}

    def tearDown(self):
        self.tmp.cleanup()

    def ledger(self):
        if not os.path.exists(self.led):
            return []
        with open(self.led, encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    def provider(self, n_ops, fail_at=None, partial=False):
        test = self

        class P:
            name, paid, contract = "llm_x", True, "edge.paid_provider.v1"
            sent = []

            def generate(self, inp, transport):
                out = None
                for i in range(n_ops):
                    out = transport.request({"op": i})
                return out

        def send(payload):
            P.sent.append(payload["op"])
            if fail_at is not None and payload["op"] == fail_at:
                raise RuntimeError("HTTP 503")
            return {"claims": []} if not partial else "{\"claims\": ["  # reponse tronquee
        return P(), send

    def test_one_reservation_per_billable_operation(self):
        from intelligence.agent_contract import run_agent
        p, send = self.provider(3)
        run_agent(p, self.inp, self.guard, send=send, max_operations=3)
        kinds = [e["event"] for e in self.ledger()]
        self.assertEqual((kinds.count("reserved"), kinds.count("attempt"), kinds.count("result")), (3, 3, 3))
        self.assertEqual(type(p).sent, [0, 1, 2])

    def test_hidden_extra_call_refused(self):
        from intelligence.agent_contract import run_agent
        from investigation.spend import SpendNotAuthorized
        p, send = self.provider(3)
        with self.assertRaises(SpendNotAuthorized):
            run_agent(p, self.inp, self.guard, send=send, max_operations=2)
        self.assertEqual(type(p).sent, [0, 1])  # la 3e operation n'est jamais emise
        self.assertEqual([e["event"] for e in self.ledger()].count("reserved"), 2)

    def test_legacy_opaque_provider_refused(self):
        from intelligence.agent_contract import run_agent
        from investigation.spend import SpendNotAuthorized

        class Legacy:
            name, paid = "llm_old", True

            def generate(self, inp):
                return {"claims": []}
        with self.assertRaises(SpendNotAuthorized):
            run_agent(Legacy(), self.inp, self.guard)
        self.assertEqual(self.ledger(), [])

    def test_failure_is_debited_and_not_silently_retried(self):
        from intelligence.agent_contract import run_agent
        p, send = self.provider(1, fail_at=0)
        with self.assertRaises(RuntimeError):
            run_agent(p, self.inp, self.guard, send=send, max_operations=1)
        ev = self.ledger()
        self.assertEqual([e["event"] for e in ev], ["reserved", "attempt", "result"])
        self.assertEqual(ev[-1]["outcome"], "error")
        self.assertEqual(type(p).sent, [0])  # aucune relance cachee

    def test_explicit_retry_reserves_again(self):
        from intelligence.agent_contract import run_agent
        p, send = self.provider(1, fail_at=0)
        with self.assertRaises(RuntimeError):
            run_agent(p, self.inp, self.guard, send=send, max_operations=1, max_attempts=2)
        self.assertEqual(type(p).sent, [0, 0])
        self.assertEqual([e["event"] for e in self.ledger()].count("reserved"), 2)

    def test_partial_response_recorded_and_rejected(self):
        from intelligence.agent_contract import PartialResponse, run_agent
        p, send = self.provider(1, partial=True)
        with self.assertRaises(PartialResponse):
            run_agent(p, self.inp, self.guard, send=send, max_operations=1)
        ev = self.ledger()
        self.assertEqual(ev[-1]["outcome"], "partial")
        self.assertEqual([e["event"] for e in ev].count("reserved"), 1)

    def test_no_request_without_authorization(self):
        from intelligence.agent_contract import run_agent
        from investigation.spend import SpendGuard, SpendNotAuthorized
        p, send = self.provider(1)
        for g in (None, SpendGuard(None)):
            with self.assertRaises(SpendNotAuthorized):
                run_agent(p, self.inp, g, send=send, max_operations=1)
        self.assertEqual(type(p).sent, [])

    def test_transport_unusable_outside_run(self):
        from intelligence.agent_contract import run_agent
        from investigation.spend import SpendNotAuthorized
        leaked = {}

        class Sneaky:
            name, paid, contract = "llm_x", True, "edge.paid_provider.v1"

            def generate(self, inp, transport):
                leaked["t"] = transport
                return transport.request({"op": 0})
        run_agent(Sneaky(), self.inp, self.guard, send=lambda p: {"claims": []}, max_operations=5)
        with self.assertRaises(SpendNotAuthorized):
            leaked["t"].request({"op": 1})  # transport ferme apres le run


if __name__ == "__main__":
    unittest.main()


class BackwardCompatibilityTests(unittest.TestCase):
    def test_schema_1_0_reports_still_valid(self):
        for n in ("pokemon_china_fictif.v1.json", "pokemon_china_fictif.v2.json"):
            r = load(n)
            self.assertEqual(r["schema_version"], "1.0.0")
            self.assertTrue(assess(r, now=T0)["valid"])

    def test_ai001_index_without_new_fields_has_no_false_positive(self):
        with tempfile.TemporaryDirectory() as d:
            s = ReportStore(os.path.join(d, "i"))
            s.publish(load())
            s.publish(load("pokemon_china_fictif.v2.json"))
            with open(s.index_path, encoding="utf-8") as f:
                idx = json.load(f)
            for e in idx["reports"]:
                for k in ("data_as_of", "max_data_age_days", "freshness_policy"):
                    e.pop(k)
            with open(s.index_path, "w", encoding="utf-8") as f:
                json.dump(idx, f)
            self.assertEqual(s.verify(), [])

    def test_assess_without_now_still_works(self):
        a = assess(load())
        self.assertIn(a["timeliness"]["status"], ("current", "stale", "unknown"))
        self.assertEqual(a["verification_level"], "simulated")
