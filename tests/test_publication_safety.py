"""Separation public/prive, fichiers generes, budget pilote et journal de couts."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from discovery.adapters import FixtureAdapter
from discovery.pipeline import run_pipeline
from edge_engine import DEFAULT_CONFIG
from tools.check_public_files import check_file, main as check_main
from tools.split_private_config import main as split_main, plan as split_plan

ROOT = os.path.join(os.path.dirname(__file__), "..")
FIX = os.path.join(ROOT, "discovery", "fixtures", "demo_observations.json")
AS_OF = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)


def write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj))


def demo_campaigns():
    with open(os.path.join(ROOT, "discovery", "demo_campaigns.json"), encoding="utf-8") as f:
        return json.load(f)["campaigns"]


class GuardTests(unittest.TestCase):
    def test_detects_private_keys_and_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "a.json"), {"x": [{"treasury": 1}]})
            write(os.path.join(d, "b.jsonl"), '{"ok": 1}\n{"execution_ready": true}\n')
            write(os.path.join(d, "c.md"), "url ?" + "token" + "=abcdefghijkl")
            write(os.path.join(d, "d.json"), {"fine": 1})
            self.assertEqual(len(check_file(os.path.join(d, "a.json"))), 1)
            self.assertEqual(len(check_file(os.path.join(d, "b.jsonl"))), 1)
            self.assertEqual(len(check_file(os.path.join(d, "c.md"))), 1)
            self.assertEqual(check_file(os.path.join(d, "d.json")), [])
            self.assertEqual(check_main([d]), 1)

    def test_tracked_files_have_no_private_data(self):
        # Garde-fou permanent : tout fichier suivi par git est public
        # (GitHub + Pages). Aucune fuite tolerée.
        from tools.check_public_files import tracked_files
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            probs = [p for f in tracked_files() for p in check_file(f)]
        finally:
            os.chdir(cwd)
        self.assertEqual(probs, [])


class SplitConfigTests(unittest.TestCase):
    def test_plan_moves_without_changing_values(self):
        pub = {"capital_monthly": 300, "capital_engaged": 0, "max_position_pct": 40}
        move, conflicts, new_pub, new_priv = split_plan(pub, {"capital_engaged": 50})
        self.assertEqual(new_pub, {"max_position_pct": 40})
        self.assertEqual(new_priv["capital_monthly"], 300)
        self.assertEqual(new_priv["capital_engaged"], 50)  # le prive existant prime
        self.assertIn("capital_engaged", conflicts)

    def test_dry_run_touches_nothing_and_apply_is_safe(self):
        with tempfile.TemporaryDirectory() as d:
            pub, priv = os.path.join(d, "config.json"), os.path.join(d, "config.private.json")
            original = {"capital_monthly": 300, "capital_max_available": 600,
                        "capital_engaged": 0, "allocation_buy_pct": [15, 40]}
            write(pub, original)
            split_main(["--public", pub, "--private", priv])
            with open(pub, encoding="utf-8") as f:
                self.assertEqual(json.load(f), original)
            self.assertFalse(os.path.exists(priv))
            split_main(["--public", pub, "--private", priv, "--apply"])
            self.assertEqual(check_file(pub), [])
            with open(priv, encoding="utf-8") as f:
                p = json.load(f)
            self.assertEqual((p["capital_monthly"], p["capital_max_available"]), (300, 600))
            self.assertNotIn("treasury", p)


class GeneratedFilesTests(unittest.TestCase):
    def run_demo(self, d, **kw):
        cfg = {**DEFAULT_CONFIG, "treasury": 1000, "engaged": 0}
        return run_pipeline(demo_campaigns(), {"fixture": FixtureAdapter(FIX)}, cfg,
                            os.path.join(d, "pub", "store"), os.path.join(d, "pub", "latest.json"),
                            os.path.join(d, "priv"), as_of=AS_OF,
                            cost_journal_path=os.path.join(d, "pub", "cost_journal.jsonl"), **kw)

    def test_public_tree_is_clean_and_private_reports_stay_private(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_demo(d)
            files = sorted(os.path.relpath(os.path.join(r, f), os.path.join(d, "pub"))
                           for r, _, fs in os.walk(os.path.join(d, "pub")) for f in fs)
            self.assertEqual(files, ["cost_journal.jsonl", "latest.json",
                                     os.path.join("store", "candidates.json"),
                                     os.path.join("store", "ledger.jsonl")])
            self.assertEqual(check_main([os.path.join(d, "pub")]), 0)
            priv_files = [f for _, _, fs in os.walk(os.path.join(d, "priv")) for f in fs]
            self.assertTrue(priv_files)
            # le rapport prive contient bien le financement
            rep = next(os.path.join(r, f) for r, _, fs in os.walk(os.path.join(d, "priv"))
                       for f in fs if f == "lego_10399.json")
            self.assertNotEqual(check_file(rep), [])

    def test_global_budget_and_cost_journal(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = self.run_demo(d, max_total_calls=2)
            executed = sum(r.get("n_calls_executed", 0) for r in out["campaigns"])
            self.assertLessEqual(executed, 2)
            self.assertIn("SKIPPED_GLOBAL_BUDGET", out["summary"]["campaign_status"])
            # Budget tronque : jamais "aucune opportunite" ; un signal deja
            # trouve reste un signal (meme regle que V4).
            self.assertNotEqual(out["posture"], "NO_OPPORTUNITY_FOUND")
            with open(os.path.join(d, "pub", "cost_journal.jsonl"), encoding="utf-8") as f:
                rows = [json.loads(l) for l in f]
            self.assertTrue(all({"campaign_id", "calls_executed", "cost_units", "duration_s",
                                 "errors", "by_source", "simulated"} <= set(r) for r in rows))
            self.assertTrue(all(r["simulated"] for r in rows if r["calls_executed"]))


class WorkflowScopeTests(unittest.TestCase):
    def test_workflows_manual_readonly_by_default(self):
        import re
        for wf in ("discovery", "searchlab"):
            with open(os.path.join(ROOT, ".github", "workflows", f"{wf}.yml"), encoding="utf-8") as f:
                s = f.read()
            self.assertNotIn("schedule:", s)
            self.assertIn("permissions:\n  contents: read", s)
            self.assertIn("if: ${{ inputs.publish }}", s)
            self.assertRegex(s, r"publish:\n\s+description:[^\n]*\n\s+required: true\n\s+default: false")
            self.assertIn("python -m tools.check_public_files", s)
            # aucune interpolation directe d'une entree utilisateur dans un run:
            for block in re.findall(r"run: \|?\n?((?:\s{10,}.*\n)+|.*\n)", s):
                self.assertNotIn("${{ inputs.", block)


if __name__ == "__main__":
    unittest.main()


class SanitizeAndRevalidationTests(unittest.TestCase):
    V3 = {"generated_at": "2026-10-12T13:01:31+00:00",
          "config": {"capital_monthly": 300, "capital_max_available": 600, "capital_engaged": 0,
                     "max_position_pct": 40, "allocation_buy_pct": [15, 40]},
          "summary": {"n_buy": 0, "total": 2, "capital_available": 600, "capital_engaged": 0,
                      "capital_monthly": 300, "decision": "CASH"},
          "products": [{"id": "a", "decision": "ERROR", "price_eur": None, "allocation_eur": [0, 0],
                        "name": "A", "thesis": "t"},
                       {"id": "b", "decision": "ERROR", "price_eur": None, "allocation_eur": [15, 45],
                        "name": "B"}],
          "trends": [], "reddit": [], "scavio_offers": []}

    def test_sanitize_dry_run_then_apply_with_backup(self):
        from tools.sanitize_legacy_radar import main as san
        with tempfile.TemporaryDirectory() as d:
            radar, bk = os.path.join(d, "radar.json"), os.path.join(d, "legacy")
            write(radar, self.V3)
            san(["--radar", radar, "--backup-dir", bk])
            with open(radar, encoding="utf-8") as f:
                self.assertEqual(json.load(f), self.V3)  # simulation : intact
            self.assertEqual(san(["--radar", radar, "--backup-dir", bk, "--apply"]), 0)
            self.assertEqual(check_file(radar), [])
            with open(radar, encoding="utf-8") as f:
                new = json.load(f)
            self.assertEqual(new["summary"]["decision"], "FAILED")  # plus de faux CASH
            self.assertEqual(new["migrated_from"]["previous_decision"], "CASH")
            self.assertEqual(new["products"][0]["thesis"], "t")  # donnees de marche conservees
            self.assertEqual(new["policy"]["allocation_buy_pct"], [15, 40])
            backups = os.listdir(bk)
            self.assertEqual(len(backups), 1)
            with open(os.path.join(bk, backups[0]), encoding="utf-8") as f:
                self.assertEqual(json.load(f), self.V3)  # original intact
            with self.assertRaises(SystemExit):  # jamais d'ecrasement de sauvegarde
                write(radar, self.V3)
                san(["--radar", radar, "--backup-dir", bk, "--apply"])

    def test_example_config_allows_zero_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json.example")
            write(p, {"treasury": 0, "engaged": 0})
            self.assertEqual(check_file(p), [])
            write(p, {"treasury": 1200})
            self.assertEqual(len(check_file(p)), 1)

    def test_revalidation_sized_to_cap_and_skips_not_counted(self):
        from discovery.campaigns import run_campaign
        from discovery.store import CandidateStore, stable_id

        class Empty:
            cost_per_call = 1

            def search(self, q, limit):
                return []
        with tempfile.TemporaryDirectory() as d:
            st = CandidateStore(os.path.join(d, "s"))
            for i in range(12):
                k = f"lego:{10000 + i}"
                st.state["candidates"][stable_id(k)] = {
                    "id": stable_id(k), "product_key": k, "name": k, "first_seen": "2026-01-01",
                    "origin_campaign": "x", "origin_family": "rarity", "campaigns": [], "sources": [],
                    "observations": [], "initial": {"decision": "WATCH"}, "evaluations": [],
                    "last_seen": "2026-01-01"}
            st.save()
            camp = {"id": "revalidation", "family": "revalidation", "queries_from": "store_revalidation",
                    "sources": ["a", "b"], "max_calls": 10, "max_expansions": 0}
            out, _, _ = run_pipeline([camp], {"a": Empty(), "b": Empty()}, DEFAULT_CONFIG,
                                     os.path.join(d, "s"), os.path.join(d, "l.json"),
                                     os.path.join(d, "p"), as_of=AS_OF)
            r = out["campaigns"][0]
            self.assertEqual(r["n_calls_executed"], 10)
            self.assertEqual(len(r["calls"]), 10)  # 5 candidats x 2 sources, rien de saute
            # Plafond plus bas que le travail prevu : les sauts sont visibles et non reussis
            res = run_campaign({"id": "cap-test", "family": "rarity", "queries": ["a", "b", "c"],
                                "sources": ["a"], "max_calls": 1}, {"a": Empty()})
            st_ = [c["status"] for c in res["run"]["calls"]]
            self.assertEqual(st_.count("SKIPPED_BUDGET"), 2)
            self.assertNotEqual(res["run"]["status"], "COMPLETED")
