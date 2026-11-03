import json
import sqlite3
from datetime import datetime, timezone

DB = "storage.db"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            source TEXT,
            captured_at TEXT,
            sold_price_avg REAL,
            sold_price_median REAL,
            sold_count_30d INTEGER,
            active_listings INTEGER,
            sell_through REAL,
            lowest_ask REAL,
            currency TEXT,
            raw_json TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_product ON market_snapshot(product_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_captured ON market_snapshot(captured_at)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS run_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_run_event_run ON run_event(run_id, id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_run_event_type ON run_event(event_type, occurred_at)")
    con.commit()
    return con


def insert_snapshots(rows):
    con = sqlite3.connect(DB)
    try:
        con.executemany("""
            INSERT INTO market_snapshot
            (product_id, source, captured_at, sold_price_avg, sold_price_median,
             sold_count_30d, active_listings, sell_through, lowest_ask, currency, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        con.commit()
    finally:
        con.close()


def append_run_event(run_id, event_type, payload=None, occurred_at=None):
    """Append-only execution journal. Payload must contain metadata, never secrets."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id requis")
    if event_type not in {"STARTED", "FINISHED"}:
        raise ValueError("event_type invalide")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("payload doit être un objet")
    timestamp = occurred_at or _utc_now()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    con = sqlite3.connect(DB)
    try:
        counts = con.execute(
            "SELECT SUM(CASE WHEN event_type='STARTED' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN event_type='FINISHED' THEN 1 ELSE 0 END) "
            "FROM run_event WHERE run_id=?",
            (run_id,),
        ).fetchone()
        started_count, finished_count = (counts[0] or 0), (counts[1] or 0)
        if event_type == "STARTED" and (started_count or finished_count):
            raise ValueError("run_id déjà utilisé")
        if event_type == "FINISHED" and (started_count != 1 or finished_count != 0):
            raise ValueError("FINISHED exige un STARTED unique et aucun FINISHED antérieur")
        con.execute(
            "INSERT INTO run_event (run_id, event_type, occurred_at, payload_json) VALUES (?,?,?,?)",
            (run_id, event_type, timestamp, encoded),
        )
        con.commit()
    finally:
        con.close()


def list_run_events(run_id):
    """Read the immutable event history for one execution."""
    con = sqlite3.connect(DB)
    try:
        rows = con.execute(
            "SELECT event_type, occurred_at, payload_json FROM run_event WHERE run_id=? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [
            {"event_type": event_type, "occurred_at": occurred_at,
             "payload": json.loads(payload_json)}
            for event_type, occurred_at, payload_json in rows
        ]
    finally:
        con.close()


def find_unfinished_runs():
    """Return STARTED runs without a later FINISHED event (e.g. killed runner)."""
    con = sqlite3.connect(DB)
    try:
        rows = con.execute("""
            SELECT run_id, MIN(occurred_at)
            FROM run_event
            GROUP BY run_id
            HAVING SUM(CASE WHEN event_type='STARTED' THEN 1 ELSE 0 END) >
                   SUM(CASE WHEN event_type='FINISHED' THEN 1 ELSE 0 END)
            ORDER BY MIN(id)
        """).fetchall()
        return [{"run_id": run_id, "started_at": started_at} for run_id, started_at in rows]
    finally:
        con.close()
