"""AI-001 : EDGE Intelligence Report v1 (schema, validateur, stockage,
graphiques, contrat d'agent). Aucun reseau : les sockets sont bloques."""
import copy
import json
import os
import socket
import tempfile
import unittest
from unittest import mock

from intelligence.agent_contract import (AgentNotConfigured, AgentOutputRejected, NullAgentProvider,
                                         build_agent_input, ingest_agent_output, run_agent)
from intelligence.charts import chart_view
from intelligence.store import PublishRefused, ReportStore, next_version
from intelligence.validator import SCHEMA, assess, content_sha256
from investigation.spend import SpendGuard, SpendNotAuthorized

ROOT = os.path.join(os.path.dirname(__file__), "..")
EX = os.path.join(ROOT, "intelligence", "examples")
_PATCH = []


def setUpModule():
    def refuse(*a, **k):
        raise AssertionError("appel reseau interdit pendant les tests")
    for target in ("socket.socket.connect", "socket.create_connection", "socket.getaddrinfo"):
        p = mock.patch(target, refuse)
        p.start()
        _PATCH.append(p)


def tearDownModule():
    for p in _PATCH:
        p.stop()


def load(name="pokemon_china_fictif.v1.json"):
    with open(os.path.join(EX, name), encoding="utf-8") as f:
        return json.load(f)


def real_report():
    """Rapport REEL minimal (valeurs neutres) : sert a prouver que le chemin
    positif complet est possible sous conditions strictes."""
    r = load()
    r.update(simulated=False, production_status="complete", report_id="eir_real-minimal")
    r["sources"] = [{"source_id": "src_editeur-a", "title": "Releve", "publisher": "Editeur A", "url": "https://example.org/a",
                     "published_at": "2026-10-01", "accessed_at": "2026-10-15", "tier": "primary", "simulated": False}]
    r["claims"] = [{"claim_id": "clm_offre", "kind": "fact", "verification": "verified", "author": "human",
                    "statement": "Offre achetable verifiee.", "source_ids": ["src_editeur-a"], "confidence": "high"},
                   {"claim_id": "clm_frais", "kind": "fact", "verification": "verified", "author": "human",
                    "statement": "Frais verifies.", "source_ids": ["src_editeur-a"], "confidence": "high"}]
    for d in r["datasets"]:
        d["simulated"] = False
        d["provenance"]["source_ids"] = ["src_editeur-a"]
        for p in d["points"]:
            if p["status"] == "simulated":
                p["status"] = "measured"
    ec = r["economics"]
    ec["availability"] = {"buyable_verified": True, "evidence_claim_ids": ["clm_offre"]}
    ec["fees"] = {"claim_ids": ["clm_frais"], "verified": True}
    ec["liquidity"] = {"claim_ids": ["clm_offre"]}
    ec["supply_demand_claim_ids"] = []
    for h in ec["roi_hypotheses"]:
        h["assumption_claim_ids"] = ["clm_frais"]
    r["decisions"] = {"agent_opinion": None,
                      "edge_decision": {"decision": "BUY", "decided_by": "edge_engine", "engine_version": "v4",
                                        "rules_applied": ["aggregate_policy"], "evidence_refs": ["lego:90001"],
                                        "decided_at": "2026-10-19T11:00:00+00:00"}}
    return r


def errs(r):
    return " | ".join(assess(r)["errors"])


class PositiveTests(unittest.TestCase):
    def test_examples_valid_and_labelled_simulated(self):
        for n in ("pokemon_china_fictif.v1.json", "pokemon_china_fictif.v2.json"):
            a = assess(load(n))
            self.assertTrue(a["valid"], a["errors"])
            self.assertEqual(a["verification_level"], "simulated")
            self.assertIn("SIMULEES", a["label"])

    def test_real_complete_report_reaches_fully_verified(self):
        # AI-001.1 : 'fully_verified' exige desormais une verification documentee.
        r = real_report()
        for c in r["claims"]:
            c["verification_record"] = {"verified_by": {"role": "human", "id": "fondateur"},
                                        "verified_at": "2026-10-18T10:00:00+00:00",
                                        "method": "primary_document_review", "procedure": "EVP-1",
                                        "evidence": [{"source_id": "src_editeur-a", "locator": "page produit"}]}
        a = assess(r)
        self.assertTrue(a["valid"], a["errors"])
        self.assertEqual(a["verification_level"], "fully_verified")

    def test_partial_never_fully_verified(self):
        r = real_report()
        r["production_status"] = "partial"
        self.assertEqual(assess(r)["verification_level"], "partially_verified")
        r = real_report()
        r["production_status"] = "draft"
        self.assertEqual(assess(r)["verification_level"], "draft")

    def test_stale_data_is_not_fully_verified(self):
        r = real_report()
        r["freshness"] = {"max_data_age_days": 1}  # data_as_of 4 j avant created_at
        a = assess(r)
        self.assertTrue(a["valid"])
        self.assertEqual(a["verification_level"], "partially_verified")
        self.assertTrue(a["warnings"])

    def test_unresolved_contradiction_blocks_fully_verified(self):
        r = real_report()
        r["sources"].append(dict(r["sources"][0], source_id="src_editeur-b"))
        r["claims"][0]["contradicting_source_ids"] = ["src_editeur-b"]
        self.assertEqual(assess(r)["verification_level"], "partially_verified")

    def test_chart_view_adds_no_value(self):
        r = load()
        v = chart_view(r, "cht_prix")
        self.assertEqual(v["watermark"], "DONNEES SIMULEES")
        ds = {d["dataset_id"]: d for d in r["datasets"]}
        for s in v["series"]:
            self.assertEqual([p["value"] for p in s["points"]], [p["value"] for p in ds[s["dataset_id"]]["points"]])
            self.assertTrue(all(p["style"] == "gap" for p in s["points"] if p["value"] is None))


class NumericTests(unittest.TestCase):
    def test_invalid_numbers_rejected(self):
        for bad in (float("nan"), float("inf"), True, "420", -5):
            r = load()
            r["datasets"][0]["points"][0]["value"] = bad
            self.assertFalse(assess(r)["valid"], repr(bad))
        r = load()
        r["economics"]["roi_hypotheses"][0]["net_roi_pct"] = float("nan")
        self.assertFalse(assess(r)["valid"])

    def test_null_value_requires_missing_status_and_reason(self):
        r = load()
        r["datasets"][0]["points"][4] = {"t": r["datasets"][0]["points"][4]["t"], "value": None, "status": "simulated"}
        self.assertIn("missing", errs(r))
        r = load()
        del r["datasets"][0]["points"][4]["missing_reason"]
        self.assertIn("missing_reason", errs(r))


class DateUnitCurrencyTests(unittest.TestCase):
    def test_dates(self):
        cases = [
            (lambda r: r.update(data_as_of="2026-10-25T00:00:00+00:00"), "posterieur a created_at"),
            (lambda r: r.update(created_at="2026-10-19T12:00:00.000000"), "fuseau"),
            (lambda r: r["datasets"][0]["points"][0].update(t="2024-01-01"), "hors periode"),
            (lambda r: r["datasets"][0]["points"][1].update(t=r["datasets"][0]["points"][0]["t"]), "strictement croissantes"),
            (lambda r: r["sources"][0].update(published_at="2026-10-16"), "posterieur a la consultation"),
            (lambda r: r["sources"][0].update(accessed_at="2026-11-01"), "posterieur a created_at"),
            (lambda r: r["datasets"][0]["period"].update(start="2026-12-01"), "debut posterieur"),
            (lambda r: r["datasets"][0]["points"][0].update(t="2026-13-01"), "date invalide"),
        ]
        for mutate, needle in cases:
            r = load()
            mutate(r)
            self.assertIn(needle, errs(r), needle)

    def test_units_and_currencies(self):
        cases = [
            (lambda r: r["datasets"][0].update(currency="XYZ"), "non reconnue"),
            (lambda r: r["datasets"][0].update(currency="eur"), "format invalide"),
            (lambda r: r["datasets"][2].update(currency="CNY"), "devise renseignee"),
            (lambda r: r["datasets"][0].update(unit="count", currency=None), "sans unite monetaire"),
            (lambda r: r["datasets"][1].update(currency="EUR"), "devises differentes"),
            (lambda r: r["datasets"][0].update(unit="EUR"), "hors de"),
        ]
        for mutate, needle in cases:
            r = load()
            mutate(r)
            self.assertIn(needle, errs(r), needle)


class ProvenanceAndSimulationTests(unittest.TestCase):
    def test_verified_fact_requires_real_primary_or_secondary_source(self):
        r = real_report()
        r["claims"][0]["source_ids"] = []
        self.assertIn("sans source", errs(r))
        r = real_report()
        r["sources"][0]["tier"] = "unverified"
        self.assertIn("sans source primaire", errs(r))
        r = real_report()
        r["sources"][0]["simulated"] = True
        self.assertIn("source simulee", errs(r))
        r = real_report()
        r["claims"][0]["kind"] = "hypothesis"
        self.assertIn("seul un fait", errs(r))
        r = real_report()
        r["sources"][0]["url"] = None
        self.assertIn("sans URL", errs(r))
        r = real_report()
        r["sources"][0]["url"] = "http://example.org"
        self.assertIn("https", errs(r))

    def test_simulated_never_passes_as_real(self):
        r = load()
        r["simulated"] = False
        self.assertIn("se declare reel", errs(r))
        r = load()
        r["datasets"][0]["points"][0]["status"] = "measured"
        self.assertIn("jamais une mesure", errs(r))
        r = real_report()
        r["datasets"][0]["points"][0]["status"] = "simulated"
        self.assertIn("point simule dans un dataset reel", errs(r))
        r = load()
        r["production_status"] = "complete"
        self.assertIn("'complete' interdit pour un rapport simule", errs(r))
        r = real_report()
        r["datasets"][0]["provenance"]["source_ids"] = []
        self.assertIn("mesure sans provenance", errs(r))

    def test_listed_vs_realized_prices_not_confused(self):
        r = load()
        r["economics"]["realized_sale_dataset_ids"] = ["ds_prix-affiche"]
        self.assertIn("n'est pas un prix de vente realisee", errs(r))

    def test_complete_with_unverified_fact_rejected(self):
        r = real_report()
        r["claims"][1]["verification"] = "unverified"
        self.assertIn("faits non verifies", errs(r))

    def test_broken_references(self):
        r = load()
        r["claims"][0]["source_ids"] = ["src_inexistante"]
        self.assertIn("reference inconnue", errs(r))
        r = load()
        r["charts"][0]["dataset_ids"] = ["ds_fantome"]
        self.assertIn("reference inconnue", errs(r))


class PolicyTests(unittest.TestCase):
    def test_allocation_never_in_a_report(self):
        r = real_report()
        r["decisions"]["edge_decision"]["allocation_eur"] = [100, 200]
        e = errs(r)
        self.assertIn("allocation", e)
        r = load()
        r["decisions"]["agent_opinion"]["allocation_eur"] = [0, 0]
        self.assertIn("allocation", errs(r))
        for key in ("treasury", "capital_available", "engaged"):
            r = load()
            r["subject"][key] = 1
            self.assertFalse(assess(r)["valid"], key)

    def test_positive_decision_requires_engine_and_evidence(self):
        cases = [
            (lambda r: r["decisions"]["edge_decision"].update(decided_by="none"), "sans moteur"),
            (lambda r: r["decisions"]["edge_decision"].update(evidence_refs=[]), "regles et ses preuves"),
            (lambda r: r["economics"]["availability"].update(buyable_verified=False, evidence_claim_ids=[]), "achetabilite non verifiee"),
            (lambda r: r["economics"].update(realized_sale_dataset_ids=[]), "sans ventes realisees"),
            (lambda r: r["decisions"]["edge_decision"].update(decided_at=None), "decided_at"),
        ]
        for mutate, needle in cases:
            r = real_report()
            mutate(r)
            self.assertIn(needle, errs(r), needle)

    def test_buy_impossible_in_simulated_report(self):
        r = load()
        r["decisions"]["edge_decision"] = real_report()["decisions"]["edge_decision"]
        self.assertIn("rapport simule", errs(r))

    def test_agent_opinion_is_never_a_decision(self):
        r = load()
        r["decisions"]["agent_opinion"]["is_decision"] = True
        self.assertFalse(assess(r)["valid"])
        r = load()
        r["decisions"]["agent_opinion"]["stance"] = "BUY"
        self.assertFalse(assess(r)["valid"])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ReportStore(os.path.join(self.tmp.name, "intel"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_publish_versions_immutably(self):
        v1, v2 = load(), load("pokemon_china_fictif.v2.json")
        e1 = self.store.publish(v1)
        self.assertEqual(e1["verification_level"], "simulated")
        with self.assertRaises(PublishRefused):
            self.store.publish(v1)  # republication interdite
        changed = copy.deepcopy(v1)
        changed["subject"]["title"] += " modifie"
        with self.assertRaises(PublishRefused):
            self.store.publish(changed)  # meme version, contenu different : interdit
        self.store.publish(v2)
        self.assertEqual(self.store.read(v1["report_id"])["report_version"], 2)
        self.assertEqual(content_sha256(self.store.read(v1["report_id"], 1)), e1["content_sha256"])
        self.assertEqual(self.store.verify(), [])

    def test_tampering_detected(self):
        e = self.store.publish(load())
        p = os.path.join(self.store.root, e["path"])
        with open(p, "r+", encoding="utf-8") as f:
            data = f.read().replace("EXEMPLE FICTIF", "EXEMPLE MODIFIE", 1)
            f.seek(0)
            f.write(data)
            f.truncate()
        self.assertIn("contenu modifie", self.store.verify()[0])

    def test_version_chain_enforced(self):
        v1 = load()
        with self.assertRaises(PublishRefused):
            self.store.publish(load("pokemon_china_fictif.v2.json"))  # v1 absente
        self.store.publish(v1)
        bad = next_version(v1, changes=[{"path": "$.subject", "reason": "test"}])
        bad["supersedes"]["content_sha256"] = "0" * 64
        bad["history"]["previous_versions"][-1]["content_sha256"] = "0" * 64
        with self.assertRaises(PublishRefused):
            self.store.publish(bad)  # empreinte differente de la version publiee
        no_reason = next_version(v1)
        self.assertIn("motiver", errs(no_reason))

    def test_invalid_or_private_never_published(self):
        r = load()
        r["simulated"] = False
        with self.assertRaises(PublishRefused):
            self.store.publish(r)
        self.assertFalse(os.path.exists(self.store.index_path))

    def test_published_tree_passes_public_guard(self):
        from tools.check_public_files import main as check
        self.store.publish(load())
        self.store.publish(load("pokemon_china_fictif.v2.json"))
        self.assertEqual(check([self.store.root]), 0)


class AgentContractTests(unittest.TestCase):
    def context(self):
        r = load()
        return {"report_id": "eir_agent-test", "subject": r["subject"], "sources": r["sources"],
                "datasets": r["datasets"], "data_as_of": r["data_as_of"], "economics": r["economics"],
                "edge_decision": r["decisions"]["edge_decision"]}

    def output(self):
        return {"claims": [{"claim_id": "clm_a1", "kind": "fact", "statement": "Affirmation de l'agent.",
                            "source_ids": ["src_marketplace-a"], "confidence": "medium"},
                           {"claim_id": "clm_frais-hypothese", "kind": "hypothesis", "statement": "Frais inconnus.",
                            "source_ids": [], "confidence": "low"},
                           {"claim_id": "clm_hyp-demande", "kind": "hypothesis", "statement": "Demande a confirmer.",
                            "source_ids": [], "confidence": "low"},
                           {"claim_id": "clm_ventes-rares", "kind": "uncertainty", "statement": "Volume faible.",
                            "source_ids": [], "confidence": "low"},
                           {"claim_id": "clm_prix-affiche-hausse", "kind": "uncertainty", "statement": "Tendance a confirmer.",
                            "source_ids": [], "confidence": "low"},
                           {"claim_id": "clm_incertitude-change", "kind": "uncertainty", "statement": "Change.",
                            "source_ids": [], "confidence": "low"}],
                "agent_opinion": {"stance": "neutral", "rationale": "Preuves insuffisantes.", "claim_ids": ["clm_a1"]},
                "chart_requests": [{"type": "line", "title": "Prix", "dataset_ids": ["ds_prix-affiche"]}]}

    def test_ingest_produces_valid_draft_never_verified(self):
        r = ingest_agent_output(self.output(), self.context(), "2026-10-19T12:00:00+00:00")
        a = assess(r)
        self.assertTrue(a["valid"], a["errors"])
        self.assertEqual(r["production_status"], "draft")
        self.assertTrue(all(c["author"] == "agent" for c in r["claims"]))
        self.assertTrue(all(c["verification"] in ("unverified", "simulated") for c in r["claims"]))
        self.assertFalse(r["decisions"]["agent_opinion"]["is_decision"])
        self.assertEqual(r["decisions"]["edge_decision"]["decision"], "NOT_EVALUATED")  # du contexte EDGE

    def test_agent_cannot_supply_numbers_sources_decisions_or_datasets(self):
        ctx = self.context()
        bad_outputs = [
            dict(self.output(), datasets=[{"dataset_id": "ds_x", "points": [{"t": "2026-01-01", "value": 1}]}]),
            dict(self.output(), edge_decision={"decision": "BUY"}),
            dict(self.output(), claims=[dict(self.output()["claims"][0], price_eur=10)]),
            dict(self.output(), claims=[dict(self.output()["claims"][0], source_ids=["src_inventee"])]),
            dict(self.output(), claims=[dict(self.output()["claims"][0], verification="verified")]),
            dict(self.output(), agent_opinion={"stance": "bullish", "rationale": "x", "claim_ids": [], "allocation_eur": [0, 50]}),
            dict(self.output(), agent_opinion={"stance": "bullish", "rationale": "x", "claim_ids": [], "target": 500}),
            dict(self.output(), chart_requests=[{"type": "line", "title": "x", "dataset_ids": ["ds_fantome"]}]),
            dict(self.output(), chart_requests=[{"type": "line", "title": "x", "dataset_ids": ["ds_prix-affiche"], "values": [1, 2]}]),
            "texte libre",
        ]
        for out in bad_outputs:
            with self.assertRaises(AgentOutputRejected, msg=str(out)[:80]):
                ingest_agent_output(out, ctx, "2026-10-19T12:00:00+00:00")

    def test_agent_input_carries_no_values_or_private_data(self):
        from edge_engine import assert_no_private_leak
        inp = build_agent_input(self.context())
        assert_no_private_leak(inp)
        self.assertTrue(all("points" not in d for d in inp["datasets"]))

    def test_null_agent_makes_no_call(self):
        with self.assertRaises(AgentNotConfigured):
            run_agent(NullAgentProvider(), {"report_id": "eir_x"})

    def test_paid_agent_goes_through_r42_lock(self):
        calls = []

        class PaidAgent:
            # AI-001.1 : contrat v1 obligatoire (acces facturable via transport EDGE)
            name, paid, contract = "llm_x", True, "edge.paid_provider.v1"

            def generate(self, inp, transport):
                calls.append(inp["report_id"])
                return transport.request({"q": inp["report_id"]})
        send = lambda payload: {"claims": []}
        inp = {"report_id": "eir_agent-test"}
        with self.assertRaises(SpendNotAuthorized):
            run_agent(PaidAgent(), inp, send=send)  # sans garde
        with self.assertRaises(SpendNotAuthorized):
            run_agent(PaidAgent(), inp, SpendGuard(None), send=send)  # garde sans autorisation
        self.assertEqual(calls, [])
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "spend.jsonl")
            g = SpendGuard({"authorized": True, "max_usd_per_run": 0.2, "est_usd_per_call": 0.1}, ledger_path=led)
            with self.assertRaises(SpendNotAuthorized):
                run_agent(PaidAgent(), inp, g, send=send)  # requete non approuvee
            g.allow(["eir_agent-test"])
            run_agent(PaidAgent(), inp, g, send=send)
            with open(led, encoding="utf-8") as f:
                kinds = [json.loads(l)["event"] for l in f]
        self.assertEqual(calls, ["eir_agent-test"])
        self.assertEqual(kinds, ["reserved", "attempt", "result"])


class CompatibilityTests(unittest.TestCase):
    def test_schema_file_is_the_validator_source(self):
        self.assertEqual(SCHEMA["properties"]["schema"]["const"], "edge.intelligence_report")
        self.assertEqual(len(SCHEMA["required"]), 16)

    def test_existing_dashboard_consumers_kept(self):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            html = f.read()
        for needle in ('getJSON("data/discovery/latest.json")', 'getJSON("data/searchlab/index.json")',
                       'fetch("radar.json', 'getJSON("data/intelligence/index.json")'):
            self.assertIn(needle.split("(")[1][:25], html)

    def test_unknown_schema_rejected(self):
        self.assertEqual(assess({"schema": "autre"})["verification_level"], "invalid")
        self.assertFalse(assess([])["valid"])


if __name__ == "__main__":
    unittest.main()
