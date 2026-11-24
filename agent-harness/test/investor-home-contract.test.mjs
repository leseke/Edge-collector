import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const dashboard = await readFile(new URL("../../app/components/MarketDashboard.tsx", import.meta.url), "utf8");
const css = await readFile(new URL("../../app/dashboard.css", import.meta.url), "utf8");

test("product content precedes educational disclosure and AI feature", () => {
  const products = dashboard.indexOf('className="edge-home-market"');
  const ai = dashboard.indexOf('className="edge-home-ai"');
  const help = dashboard.indexOf('className="edge-home-help"');
  assert.ok(products > 0 && ai > products && help > ai);
  assert.match(dashboard, /snapshot\.cards\.map/);
  assert.match(dashboard, /snapshot\.cards\.length \? /);
});
test("never advertise AI as connected or manufacture opportunities", () => {
  assert.match(dashboard, /Agent conversationnel non activé/);
  assert.match(dashboard, /Aucun prix n'est simulé/);
  assert.doesNotMatch(dashboard, /STRONG_BUY|Rendement garanti|\bBUY\b/);
});
test("market prices remain indicative and provenance is available on demand", () => {
  assert.match(dashboard, /Prix indicatif bas/);
  assert.match(dashboard, /Prix & sources/);
  assert.match(dashboard, /pas des ventes conclues/);
  assert.match(dashboard, /card\.source/);
  assert.match(dashboard, /card\.languageVerified/);
});
test("mobile layout and reduced backoffice are intentional", () => {
  assert.match(css, /\.edge-asset-grid/);
  assert.match(css, /@media\(max-width:760px\)/);
  assert.doesNotMatch(dashboard, /collection_runs|collection_errors|SQLite|auth\.token|Ollama/);
});


test("early research signals do not require a confirmed sales trend", () => {
  assert.match(dashboard, /snapshot\.reactionCases\.filter/);
  assert.match(dashboard, /item\.publications\.length > 0/);
  assert.match(dashboard, /SIGNAL FAIBLE · IMPACT NON ÉTABLI/);
  assert.match(dashboard, /publication\.url/);
  assert.match(dashboard, /date\(publication\.publishedAt\)/);
  assert.match(css, /\.edge-priority-grid/);
});
