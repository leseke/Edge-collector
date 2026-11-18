import test from "node:test";
import assert from "node:assert/strict";
import { comparableSales, listingCardKey } from "../../../app/lib/comparable-sales.ts";

const key = listingCardKey("PSA 10 Noctali VMAX", "Français • 2021 • Évolution Céleste • Unlimited • #215/203", "Évolution Céleste");
const short = "swsh7-215:fr:unlimited:psa:10";
const day = "2026-11-18";
const sale = (id, cents, date = day) => ({ id, cents, day: date, source: "https://example.test/" + id });
const variant = (key, ...paidSales) => ({ key, variant: key, paidSales });

test("catalogue and verified legacy keys agree only for matching variants", () => {
  assert.equal(key, "carte:2021:evolution-celeste:215/203:noctali-vmax:fr:unlimited:psa:10");
  assert.equal(listingCardKey("PSA 10 Noctali", "Français • 2021 • Évolution Céleste", "Évolution Céleste"), null);
  const variants = [variant(short, sale("current", 1), sale("a", 200), sale("b", 400, "2026-01-01")),
    variant(key, sale("a", 200), sale("future", 900, "2027-01-01")),
    variant(short.replace("psa:10", "pca:9"), sale("c", 10)), variant("swsh8-157:fr:unlimited:psa:10", sale("d", 100))];
  const history = comparableSales(variants, key, "current", day);
  assert.deepEqual(history.exact.map(x => x.id), ["a", "b"]);
  assert.equal(history.median, 300);
  assert.deepEqual(history.related.map(x => x.id), ["c"]);
  assert.deepEqual(comparableSales(variants, null, "current", day), history);
});

test("unidentified listings and a lone sale do not produce a median", () => {
  assert.equal(comparableSales([], null, "unknown", day), null);
  assert.equal(comparableSales([variant(short, sale("a", 100))], key, "other", day).median, null);
});
