"""EDGE MRI-004: calcul pur de continuité des observations.

Aucune I/O, aucun réseau, aucun déclenchement de collecte.
Un heartbeat d'exécution ne compte jamais comme observation de marché.
"""
from datetime import datetime, timezone


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp ISO requis")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone obligatoire")
    return parsed.astimezone(timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def assess_continuity(expected_at, observations, as_of, tolerance_minutes=10, journal_status="UNKNOWN"):
    """Associe au plus une observation exploitable à chaque fenêtre attendue.

    expected_at : liste des horaires théoriques, fournis par le scheduler.
    observations : objets {id, observed_at, usable_market_observation}.
    as_of : date de coupure ; les données futures sont exclues.

    Une observation ne peut remplir qu'une fenêtre. Un heartbeat ou un run
    réussi sans capture doit être transmis avec usable_market_observation=False.
    """
    if not isinstance(expected_at, list) or not isinstance(observations, list):
        raise ValueError("expected_at et observations doivent être des listes")
    if isinstance(tolerance_minutes, bool) or not isinstance(tolerance_minutes, (int, float)) or tolerance_minutes < 0:
        raise ValueError("tolérance invalide")

    if journal_status not in {"VERIFIED", "DEGRADED", "UNAVAILABLE", "UNKNOWN"}:
        raise ValueError("journal_status invalide")

    cut = _instant(as_of)
    expected = sorted(_instant(x) for x in expected_at)
    if len(set(expected)) != len(expected):
        raise ValueError("fenêtres attendues dupliquées")
    expected = [x for x in expected if x <= cut]

    usable = []
    seen_ids = set()
    for item in observations:
        if not isinstance(item, dict) or not {"id", "observed_at", "usable_market_observation"} <= set(item):
            raise ValueError("observation incomplète")
        if not isinstance(item["id"], str) or not item["id"].strip():
            raise ValueError("identifiant observation invalide")
        if item["id"] in seen_ids:
            raise ValueError("identifiant observation dupliqué")
        seen_ids.add(item["id"])
        if not isinstance(item["usable_market_observation"], bool):
            raise ValueError("usable_market_observation doit être booléen")
        observed = _instant(item["observed_at"])
        if item["usable_market_observation"] and observed <= cut:
            usable.append((observed, item["id"]))

    # Appariement chronologique à deux pointeurs. Pour des fenêtres et
    # observations ordonnées sur une ligne temporelle, cette stratégie
    # maximise le nombre d'appariements dans une tolérance symétrique.
    usable.sort(key=lambda x: (x[0], x[1]))
    matched_slots = {}
    slot_index = observation_index = 0
    tolerance_seconds = tolerance_minutes * 60
    while slot_index < len(expected) and observation_index < len(usable):
        slot = expected[slot_index]
        observed, observation_id = usable[observation_index]
        delta = (observed - slot).total_seconds()
        if delta < -tolerance_seconds:
            observation_index += 1
        elif delta > tolerance_seconds:
            slot_index += 1
        else:
            matched_slots[slot_index] = {
                "observed_at": _iso(observed),
                "observation_id": observation_id,
            }
            slot_index += 1
            observation_index += 1

    missed_indices = [i for i in range(len(expected)) if i not in matched_slots]
    longest_run = current_run = 0
    for index in range(len(expected)):
        if index in missed_indices:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0

    latest = max((x[0] for x in usable), default=None)
    age_minutes = round((cut - latest).total_seconds() / 60, 1) if latest else None
    total = len(expected)

    # A partial or unavailable journal cannot support a coverage claim.
    # Keep the known schedule size, but suppress observation counts and gaps.
    if journal_status != "VERIFIED":
        intervals = [
            round((expected[i + 1] - expected[i]).total_seconds() / 60, 1)
            for i in range(len(expected) - 1)
        ]
        nominal_interval = sorted(intervals)[len(intervals) // 2] if intervals else None
        return {
            "as_of": _iso(cut),
            "continuity_status": "UNKNOWN",
            "journal_status": journal_status,
            "expected_windows": total,
            "observed_windows": None,
            "missed_windows": None,
            "coverage_ratio": None,
            "missed_at": None,
            "longest_consecutive_missed_windows": None,
            "nominal_interval_minutes": nominal_interval,
            "last_observation_at": None,
            "observation_age_minutes": None,
            "heartbeat_counts_as_observation": False,
        }
    observed_count = len(matched_slots)
    coverage = observed_count / total if total else None

    if total == 0:
        status = "UNKNOWN"
    elif observed_count == total:
        status = "CONTINUOUS"
    else:
        status = "GAP"

    intervals = [
        round((expected[i + 1] - expected[i]).total_seconds() / 60, 1)
        for i in range(len(expected) - 1)
    ]
    nominal_interval = sorted(intervals)[len(intervals) // 2] if intervals else None

    return {
        "as_of": _iso(cut),
        "continuity_status": status,
        "journal_status": "VERIFIED",
        "expected_windows": total,
        "observed_windows": observed_count,
        "missed_windows": total - observed_count,
        "coverage_ratio": round(coverage, 4) if coverage is not None else None,
        "missed_at": [_iso(expected[i]) for i in missed_indices],
        "longest_consecutive_missed_windows": longest_run,
        "nominal_interval_minutes": nominal_interval,
        "last_observation_at": _iso(latest) if latest else None,
        "observation_age_minutes": age_minutes,
        "heartbeat_counts_as_observation": False,
    }
