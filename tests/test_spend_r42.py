"""R4.2 : une operation externe = une reservation ; concurrence interprocessus."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

import connectors.ebay as ebay_connector
import investigation.spend as spend
from discovery.access import GatedAdapter
from discovery.adapters import EbaySoldAdapter
from investigation.spend import PaidGate, SpendGuard, SpendNotAuthorized

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLICY = {"authorized": True, "max_usd_per_run": 0.5, "est_usd_per_call": 0.125}  # 4 appels
REG = {"ebay_sold": {"env": ["APIFY_TOKEN"], "status": "VERIFIED", "quota_per_run": 50}}


def events(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


class RealPathTests(unittest.TestCase):
    """Chemin reel : PaidGate -> GatedAdapter -> EbaySoldAdapter (reseau simule)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.led = os.path.join(self.tmp.name, "spend.jsonl")
        self.fetched = []
        self.p = mock.patch.object(ebay_connector, "fetch_sold_items",
                                   lambda q, count=50: self.fetched.append(q) or [])
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def chain(self, env=None, policy=POLICY):
        g = SpendGuard(policy, ledger_path=self.led)
        env = {"APIFY_TOKEN": "x"} if env is None else env
        inner = EbaySoldAdapter(0.92, spend_guard=g)
        return g, PaidGate("ebay_sold", GatedAdapter("ebay_sold", inner, REG, env), g)

    def test_one_operation_one_reservation(self):
        g, gate = self.chain()
        g.allow([f"LEGO {i}" for i in range(6)])
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "x"}):
            for i in range(4):
                gate.search(f"LEGO {i}")
            with self.assertRaises(SpendNotAuthorized):
                gate.search("LEGO 4")  # 5e operation > plafond de 4
        self.assertEqual(self.fetched, ["LEGO 0", "LEGO 1", "LEGO 2", "LEGO 3"])
        ev = events(self.led)
        kinds = [e["event"] for e in ev]
        self.assertEqual((kinds.count("reserved"), kinds.count("attempt"), kinds.count("result")), (4, 4, 4))
        # chaque operation : reserved -> attempt -> result, meme identifiant
        by_id = {}
        for e in ev:
            by_id.setdefault(e["reservation_id"], []).append(e["event"])
        self.assertTrue(all(v == ["reserved", "attempt", "result"] for v in by_id.values()))
        self.assertAlmostEqual(g.spent_usd, 0.5)

    def test_direct_adapter_call_refused_even_with_valid_guard(self):
        g = SpendGuard(POLICY, ledger_path=self.led)
        g.allow(["LEGO 1"])
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "x"}):
            with self.assertRaises(SpendNotAuthorized):
                EbaySoldAdapter(0.92, spend_guard=g).search("LEGO 1")
        self.assertEqual(self.fetched, [])

    def test_reservation_cannot_be_reused_or_redirected(self):
        g = SpendGuard(POLICY, ledger_path=self.led)
        g.allow(["LEGO 1", "LEGO 2"])
        ad = EbaySoldAdapter(0.92, spend_guard=g)
        rid = g.reserve("ebay_sold", "LEGO 1")
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "x"}), g.active(rid):
            with self.assertRaises(SpendNotAuthorized):
                ad.search("LEGO 2")  # reservation emise pour une autre requete
            ad.search("LEGO 1")
            with self.assertRaises(SpendNotAuthorized):
                ad.search("LEGO 1")  # deja consommee
        self.assertEqual(self.fetched, ["LEGO 1"])

    def test_blocked_before_external_call_is_released(self):
        g = SpendGuard(POLICY, ledger_path=self.led)
        g.allow(["LEGO 1"])
        gate = PaidGate("ebay_sold", GatedAdapter("ebay_sold", EbaySoldAdapter(0.92, spend_guard=g), REG, {}), g)
        with self.assertRaises(Exception):
            gate.search("LEGO 1")  # APIFY_TOKEN absent : bloque avant l'appel
        self.assertEqual(g.spent_usd, 0)
        self.assertEqual([e["event"] for e in events(self.led)], ["reserved", "released"])
        self.assertEqual(self.fetched, [])

    def test_failed_external_call_stays_debited(self):
        g = SpendGuard(POLICY, ledger_path=self.led)
        g.allow(["LEGO 1"])
        gate = PaidGate("ebay_sold", GatedAdapter("ebay_sold", EbaySoldAdapter(0.92, spend_guard=g),
                                                  REG, {"APIFY_TOKEN": "x"}), g)
        with mock.patch.object(ebay_connector, "fetch_sold_items", side_effect=RuntimeError("HTTP 500")), \
             mock.patch.dict(os.environ, {"APIFY_TOKEN": "x"}):
            with self.assertRaises(RuntimeError):
                gate.search("LEGO 1")
        ev = events(self.led)
        self.assertEqual([e["event"] for e in ev], ["reserved", "attempt", "result"])
        self.assertEqual(ev[-1]["outcome"], "error")
        self.assertAlmostEqual(g.spent_usd, 0.125)

    def test_no_ledger_no_spend(self):
        g = SpendGuard(POLICY, ledger_path=None)
        g.allow(["LEGO 1"])
        with self.assertRaises(SpendNotAuthorized):
            g.reserve("ebay_sold", "LEGO 1")

    def test_ledger_has_no_private_capital(self):
        from tools.check_public_files import check_file
        g, gate = self.chain()
        g.allow(["LEGO 1"])
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "x"}):
            gate.search("LEGO 1")
        self.assertEqual(check_file(self.led), [])


class LockTests(unittest.TestCase):
    def test_refused_when_no_lock_available(self):
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(spend, "fcntl", None), mock.patch.object(spend, "msvcrt", None):
            g = SpendGuard(POLICY, ledger_path=os.path.join(d, "s.jsonl"))
            g.allow(["LEGO 1"])
            with self.assertRaises(SpendNotAuthorized):
                g.reserve("p", "LEGO 1")
            self.assertFalse(os.path.exists(os.path.join(d, "s.jsonl")))

    @unittest.skipUnless(spend.fcntl, "verrou POSIX requis pour ce test")
    def test_refused_when_lock_held_elsewhere(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "s.jsonl")
            holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(f"""
                import fcntl, os, sys, time
                fd = os.open({led + '.lock'!r}, os.O_CREAT | os.O_RDWR)
                fcntl.flock(fd, fcntl.LOCK_EX)
                print('locked', flush=True); time.sleep(3)
                """)], stdout=subprocess.PIPE, text=True)
            self.assertEqual(holder.stdout.readline().strip(), "locked")
            try:
                g = SpendGuard(POLICY, ledger_path=led, lock_timeout=0.3)
                g.allow(["LEGO 1"])
                with self.assertRaises(SpendNotAuthorized):
                    g.reserve("p", "LEGO 1")
            finally:
                holder.kill()
                holder.wait()
                holder.stdout.close()


WORKER = textwrap.dedent("""
    import json, os, sys, time
    sys.path.insert(0, {root!r})
    from investigation.spend import SpendGuard, SpendNotAuthorized
    led, go = sys.argv[1], sys.argv[2]
    g = SpendGuard({{"authorized": True, "max_usd_per_run": 1, "est_usd_per_call": 0.125,
                     "max_usd_per_month": 1.0}}, ledger_path=led)
    g.allow(["LEGO 1"])
    while not os.path.exists(go):
        time.sleep(0.001)
    try:
        g.reserve("ebay_sold", "LEGO 1"); print("OK")
    except SpendNotAuthorized as e:
        print("REFUSED")
""")


class CiTests(unittest.TestCase):
    def test_monthly_cap_refused_in_ci(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            g = SpendGuard(dict(POLICY, max_usd_per_month=5), ledger_path=os.path.join(d, "s.jsonl"))
            g.allow(["LEGO 1"])
            with self.assertRaises(SpendNotAuthorized):
                g.reserve("p", "LEGO 1")


class ConcurrencyTests(unittest.TestCase):
    def test_two_processes_race_for_last_call(self):
        """Il reste exactement un appel sous le plafond mensuel : sur 10 manches,
        deux processus distincts le tentent simultanement ; un seul gagne."""
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).isoformat()
        for rnd in range(10):
            with tempfile.TemporaryDirectory() as d:
                led, go = os.path.join(d, "s.jsonl"), os.path.join(d, "go")
                with open(led, "w", encoding="utf-8") as f:  # 0.875 deja debite ce mois-ci
                    f.write(json.dumps({"event": "reserved", "reservation_id": "x", "at": month,
                                        "est_usd": 0.875}) + "\n")
                script = os.path.join(d, "w.py")
                with open(script, "w", encoding="utf-8") as f:
                    f.write(WORKER.format(root=ROOT))
                procs = [subprocess.Popen([sys.executable, script, led, go],
                                          stdout=subprocess.PIPE, text=True) for _ in range(2)]
                open(go, "w").close()  # depart simultane
                outs = sorted(p.communicate(timeout=30)[0].strip() for p in procs)
                self.assertEqual(outs, ["OK", "REFUSED"], f"manche {rnd}")
                total = sum(e["est_usd"] for e in events(led) if e["event"] == "reserved")
                self.assertLessEqual(total, 1.0 + 1e-9)

    def test_race_without_lock_would_overspend(self):
        """Preuve que le test de concurrence detecte le defaut : sans verrou
        (simule), les deux lectures precedent les deux ecritures."""
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "s.jsonl")
            pol = dict(POLICY, max_usd_per_month=0.125)
            a, b = SpendGuard(pol, ledger_path=led), SpendGuard(pol, ledger_path=led)
            a.allow(["LEGO 1"]); b.allow(["LEGO 1"])
            seen = [a._month_debited(), b._month_debited()]  # lectures entrelacees
            self.assertEqual(seen, [0.0, 0.0])  # les deux croiraient avoir le budget
            a.reserve("p", "LEGO 1")
            with self.assertRaises(SpendNotAuthorized):
                b.reserve("p", "LEGO 1")  # le vrai chemin relit sous verrou : refus


if __name__ == "__main__":
    unittest.main()
