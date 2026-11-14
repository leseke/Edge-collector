"""Agent d'intelligence HORS LIGNE, deterministe (AI-002A).

Implemente le contrat AI-001 (generate(agent_input) -> claims, agent_opinion,
chart_requests). Il ne fait que reorganiser des elements fournis par EDGE :
- faits = extraits de sources recopies a l'identique, avec leur source ;
- contradictions = positions divergentes sur une meme affirmation ;
- inconnues = sous-questions sans extrait ni donnee ;
- graphiques = identifiants de datasets ayant des donnees ;
- aucun chiffre, aucune decision, aucun avis favorable.
Remplacable par un modele (meme contrat, memes controles en aval).
"""


class OfflineAgentProvider:
    name = "edge_offline_agent"
    paid = False

    def generate(self, inp):
        claims, charts, used = [], [], []
        exts = inp["extracts"]
        for sq in inp["plan"]["subquestions"]:
            t = sq["topic_id"]
            mine = [e for e in exts if e["topic_id"] == t]
            dsets = [d for d in inp["datasets"] if t in inp["dataset_topics"].get(d["dataset_id"], [])
                     and inp["dataset_coverage"].get(d["dataset_id"], 0) > 0]
            if not mine and not dsets:
                claims.append({"claim_id": f"clm_inconnu-{t}", "kind": "uncertainty", "confidence": "high",
                               "source_ids": [], "statement": f"Aucune donnee autorisee ne permet de repondre a : {sq['question']}"})
                continue
            positions = {}
            for e in mine:
                positions.setdefault(e["assertion_key"], {}).setdefault(e["position"], []).append(e)
            for e in mine:
                others = [o["source_id"] for pos, lst in positions[e["assertion_key"]].items()
                          if pos != e["position"] for o in lst]
                c = {"claim_id": f"clm_{t}-{e['extract_id']}", "kind": "fact", "confidence": "low" if others else "medium",
                     "source_ids": [e["source_id"]], "statement": e["statement"]}
                if others:
                    c["contradicting_source_ids"] = sorted(set(others))
                claims.append(c)
                used.append(c["claim_id"])
            if dsets and not mine:
                claims.append({"claim_id": f"clm_sans-texte-{t}", "kind": "limitation", "confidence": "high",
                               "source_ids": [], "statement": f"Donnees chiffrees disponibles sans affirmation sourcee pour : {sq['question']}"})
            measures = {d["measure"] for d in dsets}
            if {"asking_price", "sold_price"} <= measures:
                claims.append({"claim_id": f"clm_hyp-ecart-{t}", "kind": "hypothesis", "confidence": "low", "source_ids": [],
                               "statement": "L'ecart entre prix affiches et prix realises doit etre confirme avant toute conclusion economique."})
            groups = {}
            for d in dsets:
                groups.setdefault((d["unit"], d["currency"]), []).append(d["dataset_id"])
            for (unit, cur), ids in groups.items():
                charts.append({"type": "line", "title": f"{sq['question']} ({cur or unit})", "dataset_ids": ids})
        claims.append({"claim_id": "clm_limite-automatique", "kind": "limitation", "confidence": "high", "source_ids": [],
                       "statement": "Analyse automatique hors ligne : aucune affirmation n'a ete verifiee par un humain."})
        if inp["timeliness"]["status"] == "stale":
            claims.append({"claim_id": "clm_limite-fraicheur", "kind": "limitation", "confidence": "high", "source_ids": [],
                           "statement": "Les donnees disponibles sont perimees au regard de la politique de fraicheur."})
        if inp["simulated"]:
            claims.append({"claim_id": "clm_limite-fictif", "kind": "limitation", "confidence": "high", "source_ids": [],
                           "statement": "Corpus de demonstration : donnees et sources fictives."})
        if inp["excluded_count"]:
            claims.append({"claim_id": "clm_limite-ecartes", "kind": "limitation", "confidence": "high", "source_ids": [],
                           "statement": "Des extraits de sources tierces ont ete ecartes pour contenu suspect."})
        return {"claims": claims, "chart_requests": charts,
                "agent_opinion": {"stance": "insufficient_evidence", "claim_ids": used[:5] or [claims[0]["claim_id"]],
                                  "rationale": "Analyse automatique non verifiee ; donnees partielles ou non confirmees."}}
