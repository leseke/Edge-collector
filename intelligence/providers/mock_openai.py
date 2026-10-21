"""Faux fournisseur reproduisant le CONTRAT HTTP de la Responses API.

Hors ligne, deterministe. Il remplace uniquement la fonction d'envoi HTTP :
le meme adaptateur (construction de la requete, analyse de la reponse,
reservations R4.2) est exerce que pour le vrai fournisseur.
Options d'echec : status, raw_text, refusal, extra_output_item, fail_with,
mutate(op, sortie).
"""
import json

from intelligence.computations import compute
from intelligence.providers.openai_responses import ProviderHTTPError, ProviderRateLimited, parse_response


class MockTimeout(RuntimeError):
    pass


class MockResponsesAPI:
    def __init__(self, mutate=None, status="completed", raw_text=None, refusal=False,
                 extra_output_item=None, fail_with=None):
        self.mutate, self.status, self.raw_text = mutate, status, raw_text
        self.refusal, self.extra, self.fail_with = refusal, extra_output_item, fail_with
        self.calls = []

    # --- un modele "honnete" simule
    def _plan(self, data, schema):
        allowed = schema["properties"]["topic_ids"]["items"]["enum"]
        return {"topic_ids": [t["topic_id"] for t in data["candidate_topics"] if t["topic_id"] in allowed],
                "notes": "selection des sujets pertinents"}

    def _analysis(self, data):
        facts = [{"claim_id": f"clm_m-{e['extract_id']}", "extract_id": e["extract_id"], "confidence": "medium"}
                 for e in data["extracts"]]
        comps, interps = [], []
        for d in data["datasets"]:
            if d.get("points_with_data", 0) >= 2 and d["dataset_id"] in {x for t in data["topics"]
                                                                         for x in t.get("dataset_ids", [])}:
                full = {"points": d["points"], "unit": d["unit"], "currency": d["currency"]}
                res = compute("pct_change", full, d["period"]["start"], d["period"]["end"])
                cid = f"cmp_m-{d['dataset_id'][3:]}"
                comps.append({"computation_id": cid, "method": "pct_change", "dataset_id": d["dataset_id"],
                              "t_from": d["period"]["start"], "t_to": d["period"]["end"],
                              "claimed_result": round(res["result"], 1)})
                interps.append({"claim_id": f"clm_mi-{d['dataset_id'][3:]}", "confidence": "low",
                                "statement": f"Sur la periode, la serie varie d'environ {res['result']:.1f} %.",
                                "basis_fact_ids": [], "basis_computation_ids": [cid]})
                break
        unanswered = [t for t in data["topics"] if not t.get("dataset_ids") and
                      not [e for e in data["extracts"] if e["topic_id"] == t["topic_id"]]]
        return {"facts": facts, "computations": comps, "interpretations": interps,
                "hypotheses": [{"claim_id": "clm_m-hyp", "statement": "La tendance observee doit etre confirmee par des ventes realisees.", "confidence": "low"}],
                "uncertainties": [{"claim_id": f"clm_m-inc-{t['topic_id']}", "statement": f"Aucune donnee pour : {t['question']}", "confidence": "high"} for t in unanswered],
                "limitations": [{"claim_id": "clm_m-lim", "statement": "Synthese produite par un modele, non verifiee.", "confidence": "high"}],
                "charts": [{"title": "Serie", "type": "line", "dataset_ids": [comps[0]["dataset_id"]]}] if comps else [],
                "opinion": {"stance": "insufficient_evidence", "rationale": "Preuves partielles et non verifiees."},
                "insufficient_evidence": True}

    def send(self, payload):
        self.calls.append(payload)
        op = payload["text"]["format"]["name"].replace("edge_", "")
        if self.fail_with == "rate_limit":
            raise ProviderRateLimited(429)
        if self.fail_with == "http_500":
            raise ProviderHTTPError(500)
        if self.fail_with == "timeout":
            raise MockTimeout("delai depasse")
        data = json.loads(payload["input"][0]["content"][0]["text"])["untrusted_data"]
        out = self._plan(data, payload["text"]["format"]["schema"]) if op == "plan" else self._analysis(data)
        if self.mutate:
            self.mutate(op, out)
        text = self.raw_text if self.raw_text is not None else json.dumps(out, ensure_ascii=False)
        content = [{"type": "refusal", "refusal": "non"}] if self.refusal else [{"type": "output_text", "text": text}]
        items = [{"type": "message", "role": "assistant", "content": content}]
        if self.extra:
            items.append(self.extra)
        body = {"id": f"resp_mock_{len(self.calls):04d}", "object": "response", "status": self.status,
                "incomplete_details": None if self.status == "completed" else {"reason": "max_output_tokens"},
                "output": items, "usage": {"input_tokens": 1000 + len(json.dumps(payload)) // 4, "output_tokens": 200}}
        return parse_response(body)
