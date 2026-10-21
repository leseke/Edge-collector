import unittest

import edge_engine as E

ITEM = {"id": "x", "target_buy": 100, "target_strong_buy": 80, "category": "flip"}
OFFER = {"price_eur": 790.0, "url": "https://shop.example/x"}


def cfg(**kw):
    c = dict(E.DEFAULT_CONFIG)
    c.update(kw)
    return c


class CapitalTests(unittest.TestCase):
    def test_available_is_treasury_minus_engaged(self):
        s = E.capital_state(cfg(treasury=500, engaged=120))
        self.assertEqual(s["capital_available"], 380)

    def test_available_never_negative(self):
        self.assertEqual(E.capital_state(cfg(treasury=100, engaged=300))["capital_available"], 0)

    def test_legacy_engaged_alias(self):
        self.assertEqual(E.capital_state(cfg(treasury=500, capital_engaged=200))["capital_available"], 300)

    def test_unknown_treasury_blocks_capital(self):
        s = E.capital_state(cfg())
        self.assertIsNone(s["capital_available"])
        self.assertFalse(s["capital_known"])
        self.assertEqual(E.compute_allocation_frange(cfg(), "BUY"), (0, 0))

    def test_allocation_capped_by_max_position(self):
        lo, hi = E.compute_allocation_frange(cfg(treasury=1000, engaged=0, max_position_pct=30), "BUY")
        self.assertEqual((lo, hi), (150, 300))


class IndependenceTests(unittest.TestCase):
    STRONG = {"id": "big", "target_buy": 900, "target_strong_buy": 850, "category": "flip"}

    def test_strong_buy_800_with_300_capital_is_kept(self):
        d = E.decide(self.STRONG, 800, {}, cfg(treasury=300, engaged=0), offer={"price_eur": 800})
        self.assertEqual(d["decision"], "STRONG_BUY")
        self.assertTrue(d["opportunity_alert"])
        self.assertFalse(d["capital_sufficient"])
        self.assertFalse(d["execution_ready"])
        self.assertIn("capital_insufficient", d["execution_blockers"])

    def test_decision_identical_whatever_capital(self):
        outs = {E.decide(self.STRONG, 800, {}, cfg(treasury=t, engaged=0))["decision"]
                for t in (0, 300, 10_000)}
        outs.add(E.decide(self.STRONG, 800, {}, cfg())["decision"])
        self.assertEqual(outs, {"STRONG_BUY"})

    def test_missing_capital_keeps_opportunity_but_blocks_execution(self):
        d = E.decide(self.STRONG, 800, {}, cfg(), offer={"price_eur": 800})
        self.assertTrue(d["opportunity_alert"])
        self.assertIsNone(d["capital_sufficient"])
        self.assertFalse(d["execution_ready"])

    def test_execution_ready_requires_verified_offer(self):
        c = cfg(treasury=10_000, engaged=0)
        self.assertFalse(E.decide(self.STRONG, 800, {}, c)["execution_ready"])
        self.assertTrue(E.decide(self.STRONG, 800, {}, c, offer={"price_eur": 800})["execution_ready"])

    def test_allocation_cap_blocks_execution_not_signal(self):
        c = cfg(treasury=1000, engaged=0)  # allocation max 400
        d = E.decide(self.STRONG, 800, {}, c, offer={"price_eur": 800})
        self.assertTrue(d["capital_sufficient"])
        self.assertFalse(d["allocation_sufficient"])
        self.assertFalse(d["execution_ready"])
        self.assertEqual(d["decision"], "STRONG_BUY")

    def test_invalid_config_never_executes(self):
        c = cfg(treasury=10_000, engaged=0, allocation_buy_pct=[50, 10])
        d = E.decide(self.STRONG, 800, {}, c, offer={"price_eur": 800})
        self.assertFalse(d["execution_ready"])
        self.assertIn("config_invalid", d["execution_blockers"])
        self.assertEqual(d["decision"], "STRONG_BUY")

    def test_wait_and_watch_have_no_allocation(self):
        c = cfg(treasury=10_000, engaged=0)
        for item, price in ((ITEM, 150), ({"id": "w"}, 50)):
            d = E.decide(item, price, {}, c, offer={"price_eur": price})
            self.assertIn(d["decision"], ("WAIT", "WATCH"))
            self.assertEqual(d["allocation_eur"], [0, 0])
            self.assertFalse(d["execution_ready"])

    def test_non_finite_price_is_no_data(self):
        for bad in (float("nan"), float("inf"), 0, -5, None):
            self.assertEqual(E.economic_decision(ITEM, bad)[0], "NO_DATA")


class StatusTests(unittest.TestCase):
    def p(self, d, alert=False):
        return {"id": d, "decision": d, "opportunity_alert": alert}

    def test_all_errors_is_failed_not_cash(self):
        s = E.summarize([self.p("ERROR")] * 5, cfg())
        self.assertEqual((s["data_status"], s["decision"], s["posture"]), ("FAILED", "FAILED", "NO_CONCLUSION"))

    def test_signal_never_cash_even_if_partial(self):
        s = E.summarize([self.p("BUY", True), self.p("ERROR")], cfg())
        self.assertEqual(s["decision"], "1 SIGNAL")
        self.assertEqual(s["data_status"], "PARTIAL")
        self.assertEqual(s["posture"], "SIGNALS")

    def test_partial_coverage_without_signal_is_not_cash(self):
        s = E.summarize([self.p("WAIT"), self.p("NO_DATA")], cfg())
        self.assertEqual(s["decision"], "PARTIAL")

    def test_full_coverage_no_signal_is_cash(self):
        s = E.summarize([self.p("WAIT"), self.p("WATCH")], cfg())
        self.assertEqual(s["decision"], "CASH")

    def test_configurable_coverage(self):
        prods = [self.p("WAIT")] * 4 + [self.p("ERROR")]
        self.assertEqual(E.summarize(prods, cfg(min_coverage_for_cash=0.8))["decision"], "CASH")
        self.assertEqual(E.summarize(prods, cfg())["decision"], "PARTIAL")

    def test_empty_is_no_data(self):
        self.assertEqual(E.summarize([], cfg())["decision"], "NO_DATA")

    def test_unknown_decision_rejected(self):
        with self.assertRaises(E.InconsistentCounters):
            E.summarize([self.p("MAYBE")], cfg())

    def test_source_failure_marks_partial(self):
        s = E.summarize([self.p("WAIT")], cfg(), sources_failed={"scavio"})
        self.assertEqual(s["data_status"], "PARTIAL")


class PrivacyTests(unittest.TestCase):
    def test_public_view_strips_funding(self):
        prod = {"id": "a", "decision": "BUY", "allocation_eur": [10, 20],
                "capital_sufficient": True, "allocation_sufficient": False,
                "execution_ready": False, "execution_blockers": ["x"]}
        pub = E.public_product_view(prod)
        E.assert_no_private_leak(pub)
        self.assertEqual(set(pub), {"id", "decision"})

    def test_leak_detector(self):
        with self.assertRaises(ValueError):
            E.assert_no_private_leak({"a": [{"treasury": 1}]})
        with self.assertRaises(ValueError):
            E.assert_no_private_leak({"config": {"capital_monthly": 300}})

    def test_policy_has_no_amounts(self):
        pol = E.public_policy(cfg(treasury=999, engaged=1))
        E.assert_no_private_leak(pol)


class LegacyCompatTests(unittest.TestCase):
    def test_estimate_cycle_unchanged(self):
        self.assertEqual(E.estimate_cycle(80, 100, 2), (1, "Invisibilite"))
        self.assertEqual(E.estimate_cycle(200, 100, 10), (7, "Capitulation"))
        self.assertEqual(E.estimate_cycle(None, 100, 1), (0, "Inconnu"))

    def test_decide_keeps_legacy_keys(self):
        d = E.decide(ITEM, 90, {"sold_price_median": 90}, cfg())
        for k in ("decision", "message", "allocation_eur", "cycle_num",
                  "cycle_label", "categorie", "ecart_pct"):
            self.assertIn(k, d)
        self.assertEqual(d["decision"], "BUY")
        self.assertEqual(d["ecart_pct"], -10.0)


if __name__ == "__main__":
    unittest.main()
