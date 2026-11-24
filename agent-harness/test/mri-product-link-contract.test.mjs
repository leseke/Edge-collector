import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read = path => readFile(new URL(path, import.meta.url), "utf8");
const [market, product, radar] = await Promise.all([read("../../app/lib/market-data.ts"), read("../../app/explorer/[productId]/page.tsx"), read("../../app/components/MarketReactionDashboard.tsx")]);
test("MRI summaries come from SHA-verified snapshot, not synthetic fixtures", () => {
  assert.match(market, /sha256\(mriText\) !== mriEntry\.sha256/);
  assert.match(market, /reactionCases: ReactionCaseSummary\[\]/);
  assert.match(market, /publication_evidence/);
  assert.match(market, /reactionCases: \[\]/);
});
test("product lookup matches exact product ID and distinguishes no investigation", () => {
  assert.match(product, /snapshot\.reactionCases\.find\(item => item\.productId === productId\)/);
  assert.match(product, /Aucun dossier MRI lié/);
  assert.match(product, /sans potentiel/);
});
test("radar links source publications but does not imply causality", () => {
  assert.match(radar, /snapshot\.reactionCases\.filter\(item => item\.productId\.startsWith\("pokemon_card_"\)\)/);
  assert.match(radar, /pokemonCases\.map/);
  assert.match(radar, /publication\.url/);
  assert.match(radar, /aria-label="Rubriques du Radar"/);
  for (const tab of ["signaux", "offres", "ventes", "marche"]) {
    assert.ok(radar.includes(`id: "${tab}"`), `Missing Radar tab: ${tab}`);
  }
  assert.ok(radar.includes('href={`/mri?tab=${item.id}`}'));
  assert.ok(radar.includes('aria-current={tab === item.id ? "page" : undefined}'));
  for (const section of ["ventes-payees", "gcc-closed", "disponibilite", "gcc-auction", "gcc-fixed"]) {
    assert.ok(radar.includes(`id="${section}"`), `Missing section: ${section}`);
  }
  assert.match(radar, /tab === "ventes" &&/);
  assert.match(radar, /tab === "offres" &&/);
  assert.match(radar, /tab === "marche" &&/);
  assert.match(radar, /Son impact commercial reste à vérifier/);
  assert.match(radar, /Aucun rendement présumé/);
});
