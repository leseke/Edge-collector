import test from "node:test";
import assert from "node:assert/strict";
import { parseLeboncoinAlert, combineAlerts, collectGraphAlerts } from "../src/leboncoin-email.mjs";

// Synthetic layout fixture. Not market evidence.
const alertBody = `[Voir les résultats : "Pokémon 30 ans"](https://www.leboncoin.fr/mes-recherches/example)
---
| [
Dracaufeu 30 ans
160 €
Paris 75020
](https://www.leboncoin.fr/vi/1234567890.htm#tracking)
---
| [
Magicarpe
90 €
Lille 59000
](https://www.leboncoin.fr/vi/1234567891.htm)
`;
const msg = (subject = "Pokémon 30 ans : 990 nouveaux résultats") => ({
  id: "mail-1", subject, receivedDateTime: "2026-11-19T05:21:31Z",
  body: { contentType: "html", content: alertBody }
});
test("parses actual link shape without treating summary as inventory", () => {
  const r = parseLeboncoinAlert(msg());
  assert.equal(r.advertised_count, 990);
  assert.equal(r.extracted_count, 2);
  assert.equal(r.truncated_email, true);
  assert.equal(r.listings[0].id, "leboncoin:1234567890");
  assert.equal(r.listings[0].price_cents, 16000);
  assert.equal(r.listings[0].price_kind, "LISTING");
  assert.equal(r.listings[0].availability, "UNVERIFIED");
  assert.equal(r.listings[1].price_cents, 9000);
});
test("ignores non-alert account emails", () => {
  assert.equal(parseLeboncoinAlert(msg("Votre code de vérification")), null);
});
test("aggregates overlapping saved searches by stable listing ID", () => {
  const a = parseLeboncoinAlert(msg());
  const b = parseLeboncoinAlert({...msg("cartes Pokémon : 2 727 nouveaux résultats"), id:"mail-2"});
  const rows = combineAlerts([a,b]);
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0].searches, ["Pokémon 30 ans","cartes Pokémon"]);
});
test("rejects cross-origin pagination", async () => {
  await assert.rejects(
    collectGraphAlerts({token:"fixture",fetchImpl:async () => ({
      ok:true, json:async () => ({value:[msg()], "@odata.nextLink":"https://example.com/leak"})
    })}),
    /unsafe_graph_pagination_url/
  );
});
test("bounded Graph retrieval reports partial without hiding unvisited pages", async () => {
  let pages = 0;
  const result = await collectGraphAlerts({token:"fixture",maxPages:1,fetchImpl: async () => {
    pages++;
    return {ok:true,json:async () => ({value:[msg()], "@odata.nextLink":"https://graph.microsoft.com/v1.0/me/messages?page=2"})};
  }});
  assert.equal(pages,1);
  assert.equal(result.status,"PARTIAL");
  assert.equal(result.listings.length,2);
  assert.equal(result.remaining_pages_possible,true);
});
