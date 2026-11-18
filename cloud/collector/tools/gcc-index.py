"""Generate an additive D1 import from GCC's public lot sitemap."""
import re
import sys
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

source = Path(sys.argv[1])
if source.stat().st_size > 24_000_000:
    raise SystemExit("Sitemap too large")
xml = source.read_bytes()
if b"<!DOCTYPE" in xml.upper():
    raise SystemExit("Unexpected sitemap structure")
root = ElementTree.fromstring(xml)
ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
lots = {}
for row in root.findall(ns + "url"):
    loc = row.findtext(ns + "loc", "")
    match = re.fullmatch(r"https://gradedcardcenter\.com/item/([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})", loc)
    modified = row.findtext(ns + "lastmod", "")
    if not match or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", modified):
        continue
    date.fromisoformat(modified)
    lot = match[1]
    lots[lot] = max(lots.get(lot, ""), modified)

if not 1 <= len(lots) <= 24_000:
    raise SystemExit("Unexpected number of public lots")
rows = sorted(lots.items())
with Path(sys.argv[2]).open("w") as sql:
    for offset in range(0, len(rows), 200):
        values = ",".join(f"('{lot}','{modified}')" for lot, modified in rows[offset:offset + 200])
        sql.write(f"INSERT INTO gcc_public_index(lot_id,source_modified_day) VALUES {values}"
                  " ON CONFLICT(lot_id) DO UPDATE SET source_modified_day=excluded.source_modified_day"
                  " WHERE excluded.source_modified_day > gcc_public_index.source_modified_day;\n")
print(f"Public GCC sitemap: {len(lots)} unique indexed lots")
