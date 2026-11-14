"""Memoire d'EDGE : journal append-only + etat des candidats.

- ledger.jsonl : evenements immuables (decouverte, observation,
  decision initiale figee, changement). Jamais reecrit.
- candidates.json : etat courant reconstruit, ecrit atomiquement.

Anti-biais retrospectif : la these et la decision initiales sont
figees a la premiere evaluation ; les reevaluations s'ajoutent sans
les remplacer.
"""
import hashlib
import json
import os

from edge_io import append_jsonl, atomic_write_json


def stable_id(product_key):
    return "edge_" + hashlib.sha256(product_key.encode("utf-8")).hexdigest()[:16]


class CandidateStore:
    def __init__(self, root):
        self.root = root
        self.ledger_path = os.path.join(root, "ledger.jsonl")
        self.state_path = os.path.join(root, "candidates.json")
        self.state = {"schema_version": 1, "candidates": {}}
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as f:
                self.state = json.load(f)

    def _event(self, kind, at, **data):
        append_jsonl(self.ledger_path, {"event": kind, "at": at, **data})

    def record_campaign(self, run_result):
        run = run_result["run"]
        at = run.get("finished_at") or run["started_at"]
        self._event("campaign_run", at, campaign_id=run["campaign_id"],
                    family=run["family"], status=run["status"],
                    n_calls=run.get("n_calls_executed"), n_errors=run.get("n_errors"),
                    cost_units=run["cost_units"], simulated=run.get("simulated", False))
        disc = run_result.get("discovery") or {"candidates": []}
        new = 0
        for c in disc["candidates"]:
            new += self._upsert(c, run, at)
        self.save()
        return new

    def _upsert(self, c, run, at):
        cid = stable_id(c["product_key"])
        cands = self.state["candidates"]
        is_new = cid not in cands
        if is_new:
            cands[cid] = {
                "id": cid, "product_key": c["product_key"], "name": c["name"],
                "first_seen": c["observed_at"], "discovered_at": at,
                "origin_campaign": run["campaign_id"], "origin_family": run["family"],
                "campaigns": [], "sources": [], "observations": [],
                "initial": None, "evaluations": [], "simulated": c.get("simulated", False),
            }
            self._event("discovered", at, candidate_id=cid, product_key=c["product_key"],
                        campaign_id=run["campaign_id"])
        rec = cands[cid]
        for field, val in (("campaigns", run["campaign_id"]), ("sources", c["source"])):
            if val not in rec[field]:
                rec[field].append(val)
        seen = {o["obs_id"] for o in rec["observations"]}
        if c["id"] not in seen:
            obs = {"obs_id": c["id"], "observed_at": c["observed_at"], "source": c["source"],
                   "evidence_type": c["evidence_type"], "price_eur": c["price_eur"],
                   "shipping_eur": c.get("shipping_eur"), "url": c["source_url"],
                   "name": c["name"], "simulated": c.get("simulated", False),
                   "product_key": c["product_key"],
                   "identity_confidence": c.get("identity_confidence")}
            for k in ("aggregate", "availability", "signal"):
                if c.get(k) is not None:
                    obs[k] = c[k]
            rec["observations"].append(obs)
            self._event("observation", at, candidate_id=cid, **obs)
        rec["last_seen"] = max(rec.get("last_seen") or "", c["observed_at"])
        return 1 if is_new else 0

    def record_evaluation(self, product_key, at, decision, confidence, reference_price_eur,
                          thesis, scenarios=None, strategy=None):
        cid = stable_id(product_key)
        rec = self.state["candidates"].get(cid)
        if rec is None:
            raise KeyError(product_key)
        ev = {"at": at, "decision": decision, "confidence": confidence,
              "reference_price_eur": reference_price_eur, "strategy": strategy,
              "thesis": thesis, "scenarios": scenarios}
        if rec["initial"] is None:
            rec["initial"] = ev  # fige : jamais reecrit
            self._event("initial_decision", at, candidate_id=cid,
                        **{k: v for k, v in ev.items() if k != "at"})
        else:
            prev = rec["evaluations"][-1] if rec["evaluations"] else rec["initial"]
            if prev["decision"] != decision or prev["confidence"] != confidence:
                self._event("decision_changed", at, candidate_id=cid,
                            previous=prev["decision"], new=decision, confidence=confidence)
        rec["evaluations"].append(ev)
        self.save()

    def get(self, product_key):
        return self.state["candidates"].get(stable_id(product_key))

    def save(self):
        atomic_write_json(self.state_path, self.state)

    def to_revalidate(self, limit=10):
        """Candidats a re-interroger (famille 'revalidation') : ceux deja
        evalues positivement ou en WATCH, les plus anciens d'abord."""
        recs = [r for r in self.state["candidates"].values()
                if r["initial"] and r["initial"]["decision"] in ("BUY", "STRONG_BUY", "WATCH")]
        recs.sort(key=lambda r: r.get("last_seen") or "")
        return recs[:limit]
