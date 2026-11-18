"""Import dated public Pokémon guide snapshots and compare indicative windows."""
import argparse
import hashlib
import json
import sqlite3
import statistics
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "https://downloads.s3.cardmarket.com/productCatalog/"
FILES = {
    "guide": "priceGuide/price_guide_6.json",
    "singles": "productList/products_singles_6.json",
    "sealed": "productList/products_nonsingles_6.json",
}
KINDS = {
    51: "CARTE", 52: "BOOSTER", 53: "DISPLAY", 1083: "BLISTER",
    1015: "COFFRET", 1016: "ETB", 1014: "TIN", 54: "DECK", 1013: "KIT",
}
MAX_BYTES = 32 * 1024 * 1024

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS guide_days (
  day TEXT PRIMARY KEY, guide_sha TEXT NOT NULL, singles_sha TEXT NOT NULL,
  sealed_sha TEXT NOT NULL, source_created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS guide_prices (
  day TEXT NOT NULL REFERENCES guide_days(day), product INTEGER NOT NULL,
  finish TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
  trend INTEGER, avg7 INTEGER, avg30 INTEGER,
  PRIMARY KEY(product, finish, day)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS guide_prices_day ON guide_prices(day);
CREATE TRIGGER IF NOT EXISTS protect_guide_prices_update BEFORE UPDATE ON guide_prices
BEGIN SELECT RAISE(ABORT, 'immutable_guide_price'); END;
CREATE TRIGGER IF NOT EXISTS protect_guide_prices_delete BEFORE DELETE ON guide_prices
BEGIN SELECT RAISE(ABORT, 'immutable_guide_price'); END;
"""


def source_document(kind, directory=None):
    if directory:
        with (Path(directory) / (kind + ".json")).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    else:
        request = Request(BASE_URL + FILES[kind], headers={"Accept": "application/json", "User-Agent": "EDGE-MarketResearch/1.0"})
        with urlopen(request, timeout=45) as response:
            if response.geturl() != request.full_url:
                raise ValueError("unexpected_source_redirect")
            raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("source_too_large")
    doc = json.loads(raw, parse_float=Decimal)
    if type(doc.get("version")) is not int or doc["version"] != 1:
        raise ValueError("unsupported_guide_version")
    field = "priceGuides" if kind == "guide" else "products"
    if not isinstance(doc.get(field), list) or not doc[field]:
        raise ValueError("empty_source_data")
    return doc, hashlib.sha256(raw).hexdigest()


def cents(value):
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite() or not 0 < value <= 1_000_000:
        return None
    rounded = int((Decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return rounded or None


def catalog_index(singles, sealed):
    index = {}
    for listing in (singles["products"], sealed["products"]):
        for row in listing:
            product, category, name = row.get("idProduct"), row.get("idCategory"), row.get("name")
            if type(product) is not int or product <= 0 or type(category) is not int or category not in KINDS:
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            identity = (category, name.strip())
            if product in index and index[product] != identity:
                raise ValueError("conflicting_product_identity")
            index[product] = identity
    return index


def import_guide(db, documents, today):
    guide, guide_sha = documents["guide"]
    created = datetime.fromisoformat(guide["createdAt"])
    if created.tzinfo is None or created.date() > today:
        raise ValueError("invalid_guide_date")
    day = created.date().isoformat()
    singles, singles_sha = documents["singles"]
    sealed, sealed_sha = documents["sealed"]
    db.executescript(SCHEMA)
    db.execute("BEGIN IMMEDIATE")
    try:
        prior = db.execute("SELECT guide_sha FROM guide_days WHERE day=?", (day,)).fetchone()
        if prior:
            if prior[0] != guide_sha:
                raise ValueError("conflicting_same_day_guide")
            db.commit()
            return day, False
        catalog = catalog_index(singles, sealed)
        db.execute("INSERT INTO guide_days VALUES (?,?,?,?,?)", (day, guide_sha, singles_sha, sealed_sha, created.isoformat()))
        rows = []
        seen = set()
        for row in guide["priceGuides"]:
            product, category = row.get("idProduct"), row.get("idCategory")
            if type(product) is not int or type(category) is not int or product not in catalog:
                continue
            known_category, name = catalog[product]
            if category != known_category:
                continue
            if product in seen:
                raise ValueError("duplicate_guide_product")
            seen.add(product)
            finishes = (("STANDARD", ""), ("HOLO", "-holo")) if category == 51 else (("SEALED", ""),)
            for finish, suffix in finishes:
                values = tuple(cents(row.get(key + suffix)) for key in ("trend", "avg7", "avg30"))
                if any(value is not None for value in values):
                    rows.append((day, product, finish, KINDS[category], name, *values))
        if not rows:
            raise ValueError("no_priced_products")
        db.executemany("INSERT INTO guide_prices VALUES (?,?,?,?,?,?,?,?)", rows)
        db.commit()
        return day, True
    except Exception:
        db.rollback()
        raise


def coverage(db, day):
    result = {}
    for kind, products, finishes in db.execute(
        "SELECT kind,COUNT(DISTINCT product),COUNT(*) FROM guide_prices WHERE day=? GROUP BY kind", (day,)
    ):
        result[kind] = {"products": products, "quotes": finishes}
    return result


def compare_history(db, product, finish, day):
    """Compare daily trend prices, excluding days beyond the report date."""
    end = date.fromisoformat(day)
    cut = (end - timedelta(days=29)).isoformat()
    start = (end - timedelta(days=59)).isoformat()
    recent, prior = [], []
    for observed, amount in db.execute(
        "SELECT day,trend FROM guide_prices WHERE product=? AND finish=? AND day BETWEEN ? AND ? AND trend IS NOT NULL",
        (product, finish, start, day),
    ):
        (recent if observed >= cut else prior).append(amount)
    result = {"recent_days": len(recent), "prior_days": len(prior), "change_pct": None}
    if min(len(recent), len(prior)) >= 7:
        before, after = statistics.median(prior), statistics.median(recent)
        result.update(prior_median_cents=before, recent_median_cents=after,
                      change_pct=round(100 * (after - before) / before, 2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--input-dir", help="Use previously downloaded official JSON exports.")
    parser.add_argument("--product", type=int, help="Cardmarket product ID for an optional analysis.")
    parser.add_argument("--finish", choices=("STANDARD", "HOLO", "SEALED"), default="STANDARD")
    args = parser.parse_args()
    with sqlite3.connect(args.db, timeout=30) as db:
        documents = {kind: source_document(kind, args.input_dir) for kind in FILES}
        day, inserted = import_guide(db, documents, datetime.now(timezone.utc).date())
        report = {"source": BASE_URL + FILES["guide"], "price_kind": "AGGREGATE", "currency": "EUR",
                  "guide_day": day, "inserted": inserted, "coverage": coverage(db, day)}
        if args.product:
            quote = db.execute(
                "SELECT name,trend,avg7,avg30 FROM guide_prices WHERE product=? AND finish=? AND day=?",
                (args.product, args.finish, day),
            ).fetchone()
            report["product"] = {"id": args.product, "finish": args.finish, "quote": quote,
                                 "history": compare_history(db, args.product, args.finish, day)}
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
