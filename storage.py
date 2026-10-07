import sqlite3

DB = "storage.db"

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
    con.commit()
    return con

def insert_snapshots(rows):
    con = sqlite3.connect(DB)
    con.executemany("""
        INSERT INTO market_snapshot
        (product_id, source, captured_at, sold_price_avg, sold_price_median,
         sold_count_30d, active_listings, sell_through, lowest_ask, currency, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    con.close()
