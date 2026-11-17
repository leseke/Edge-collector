"""Local-only D1 SQLite schema integration fixture. Never represents real market prices."""
import json
import sqlite3
from pathlib import Path
con = sqlite3.connect(":memory:")
con.executescript(Path("cloud/collector/schema.sql").read_text())
con.execute("INSERT INTO collection_runs(run_id,started_at,status) VALUES (?,?,?)", ("ci-local", "2026-11-17T10:00:00Z", "OK"))
con.execute("""INSERT INTO observations
 (observation_id,run_id,product_id,source,observed_at,price_cents,currency,availability,price_kind,source_url,payload_sha256)
 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
 ("ci-local-obs","ci-local","pokemon_card_base1_4","TCGDEX","2026-11-17T10:00:00Z",1234,"EUR","UNKNOWN","AGGREGATE","https://api.tcgdex.net/v2/fr/cards/base1-4","fixture-digest"))
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute("""SELECT product_id,price_kind,currency,source_url,observed_at,price_cents
 FROM observations WHERE price_kind='AGGREGATE' AND currency='EUR' ORDER BY observed_at DESC LIMIT 500""")]
assert len(rows) == 1
print(json.dumps([{"success": True, "results": rows}]))
